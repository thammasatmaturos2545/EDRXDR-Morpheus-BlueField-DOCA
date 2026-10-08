"""Compare actual Morpheus preprocessing/inference with HF on development data only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SourceFrames(list):
    """Keep Morpheus constructor logging from rendering GPU dataframes.

    Rendering a cuDF frame implicitly calls to_pandas in this runtime. The
    ordinary list behavior used by InMemorySourceStage remains intact.
    """
    def __repr__(self):
        return f"SourceFrames(count={len(self)})"

    __str__ = __repr__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-snapshot", type=Path,
                        help="Verify and reconstruct text from raw archives")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    report = json.loads((args.checkpoint / "training_report.json").read_text())
    if report.get("smoke") is not False or report.get("max_length") != 256:
        raise ValueError("Require full v2 checkpoint at length 256")
    if not (args.checkpoint / "RUN_COMPLETE").is_file():
        raise ValueError("Checkpoint is incomplete")
    manifest_path = args.dataset / "manifest.json"
    if digest(manifest_path) != report["dataset_manifest_sha256"]:
        raise ValueError("Dataset does not match checkpoint")
    manifest = json.loads(manifest_path.read_text())
    data = {}
    for split in ("train", "validation"):
        path = args.dataset / f"wazuh-nlp-{split}.jsonl"
        if digest(path) != manifest["output_sha256"][path.name]:
            raise ValueError("Dataset file hash mismatch")
        with path.open(encoding="utf-8") as stream:
            data[split] = [json.loads(line) for line in stream]

    raw_report = None
    if args.raw_snapshot is not None:
        from raw_event_contract import reconstruct
        raw_report = reconstruct(args.raw_snapshot, manifest, data)

    import numpy as np
    import cupy as cp
    import cudf
    import torch
    import transformers
    import morpheus
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from morpheus.config import Config, PipelineModes, ExecutionMode
    from morpheus.pipeline.linear_pipeline import LinearPipeline
    from morpheus.stages.input.in_memory_source_stage import InMemorySourceStage
    from morpheus.stages.preprocess.deserialize_stage import DeserializeStage
    from morpheus.stages.preprocess.preprocess_nlp_stage import PreprocessNLPStage
    from morpheus.stages.output.in_memory_sink_stage import InMemorySinkStage
    from morpheus_context_inference import ContextSeverityInferenceStage
    from morpheus_bert_special_tokens import BertSpecialTokensStage

    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, local_files_only=True)
    if (tokenizer.cls_token_id, tokenizer.sep_token_id, tokenizer.pad_token_id) != (101, 102, 0):
        raise ValueError("Special-token adapter requires the verified uncased BERT IDs")
    samples = [(r["text_input"], "validation") for r in data["validation"]]
    first_rule = set()
    for start in range(0, len(data["train"]), 64):
        batch = data["train"][start:start+64]
        tokens = tokenizer([r["text_input"] for r in batch], truncation=False,
                           padding=False, verbose=False)["input_ids"]
        for row, ids in zip(batch, tokens):
            first = row["rule_id"] not in first_rule
            first_rule.add(row["rule_id"])
            if first or len(ids) > 256:
                samples.append((row["text_input"], "train_coverage"))
    stress = ["Description: Mixed CASE SSH Login\nLog: /var/log/auth.log 192.0.2.1",
              "Description: spaces\tand tabs\nLog: user=root   result=ok",
              "Description: Unicode café กรุงเทพฯ\nLog: résumé",
              "", "Description: Long package list\nLog: " + "package installed " * 400]
    samples.extend((text, "synthetic_tokenizer_check") for text in stress)
    if raw_report is not None:
        from raw_event_contract import missing_field_samples
        samples.extend((text, "synthetic_missing_fields")
                       for text in missing_field_samples())
    args.output.mkdir(parents=True, exist_ok=False)
    # Separate model for the HF reference; evaluated with the same batch/precision contract.
    reference = AutoModelForSequenceClassification.from_pretrained(
        args.checkpoint, local_files_only=True, use_safetensors=True
    ).cuda().eval()
    use_bf16 = bool(report.get("bf16")) and torch.cuda.is_bf16_supported()
    references = {}
    seen_pre = Counter()
    seen_out = Counter()
    issues = []
    first_issues = []
    comparisons = []
    def note(reason, ids, details=None):
        issues.append(reason)
        if len(first_issues) < 12:
            first_issues.append({"issue": reason, "audit_ids": [int(i) for i in ids[:8]],
                                 "sources": [samples[int(i)][1] for i in ids[:8]], "details": details})

    class CheckTokensStage(InMemorySinkStage):
        @property
        def name(self):
            return "check-hf-token-parity"

        def _append_message(self, message):
            frame = message.payload().get_data()
            ids = frame["audit_id"].to_arrow().to_pylist()
            texts = frame["text_input"].to_arrow().to_pylist()
            if any(not 0 <= i < len(samples) or texts[j] != samples[i][0] for j, i in enumerate(ids)):
                raise ValueError("Input row/text alignment changed")
            seen_pre.update(ids)
            expected = tokenizer(texts, max_length=256, truncation=True,
                                 padding="max_length", return_tensors="pt")
            actual_ids = message.tensors().get_tensor("input_ids").get()
            actual_mask = message.tensors().get_tensor("input_mask").get()
            sequences = message.tensors().get_tensor("seq_ids").get()
            token_failed = False
            for field, actual, target in (
                ("input_ids", actual_ids, expected["input_ids"].numpy()),
                ("attention_mask", actual_mask, expected["attention_mask"].numpy()),
            ):
                if not np.array_equal(actual, target):
                    token_failed = True
                    bad = np.flatnonzero(np.any(actual != target, axis=1)).tolist() if actual.shape == target.shape else list(range(len(ids)))
                    note(field + "_mismatch", [ids[i] for i in bad], dict(
                        actual_shape=list(actual.shape), expected_shape=list(target.shape),
                        differing_rows=len(bad),
                        differing_positions=int(np.count_nonzero(actual != target)) if actual.shape == target.shape else None,
                        actual_mask_counts=actual_mask.sum(axis=1).tolist() if actual_mask.ndim == 2 else None,
                        expected_mask_counts=expected["attention_mask"].sum(dim=1).tolist(),
                    ))
            if sequences.shape[0] != len(ids) or not np.array_equal(sequences[:, 0], np.arange(len(ids))):
                token_failed = True
                note("sequence_row_mapping_mismatch", ids)
            if token_failed:
                raise ValueError("Token parity failed before inference; see first_issues in parity_report.json")
            for start in range(0, len(ids), 8):
                batch = {key: value[start:start+8].cuda() for key, value in expected.items()}
                with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_bf16):
                    logits = reference(**batch).logits.float()
                if not torch.isfinite(logits).all().item():
                    raise ValueError("Nonfinite reference score")
                scores = logits.sigmoid().cpu().numpy().reshape(-1)
                references.update(zip(ids[start:start+8], scores.tolist()))
            return message

    config = Config()
    config.mode = PipelineModes.NLP
    config.execution_mode = ExecutionMode.GPU
    config.feature_length = 256
    config.num_threads = 1
    config.pipeline_batch_size = 16
    config.model_max_batch_size = 8
    config.class_labels = ["high_severity_score"]
    frame = cudf.DataFrame({"audit_id": list(range(len(samples))),
                           "text_input": [s[0] for s in samples]})
    # Uneven source frames exercise row alignment, inference mini-batches and tail batches.
    # Exercise the Arrow transfer now, before building the pipeline.
    if frame["audit_id"].to_arrow().to_pylist() != list(range(len(samples))):
        raise ValueError("Arrow audit-ID transfer changed row ordering")
    source_frames = SourceFrames([frame.iloc[:1].copy(), frame.iloc[1:18].copy(), frame.iloc[18:].copy()])
    pipeline = LinearPipeline(config)
    pipeline.set_source(InMemorySourceStage(config, source_frames))
    pipeline.add_stage(DeserializeStage(config))
    pipeline.add_stage(PreprocessNLPStage(
        config, vocab_hash_file="data/bert-base-uncased-hash.txt", truncation=True,
        do_lower_case=True, add_special_tokens=False, column="text_input"
    ))
    pipeline.add_stage(BertSpecialTokensStage(config))
    pipeline.add_stage(CheckTokensStage(config))
    pipeline.add_stage(ContextSeverityInferenceStage(config, args.checkpoint))
    sink = pipeline.add_stage(InMemorySinkStage(config))
    print(json.dumps({"phase": "running_offline_pipeline", "rows": len(samples),
                      "sources": dict(Counter(s[1] for s in samples))}), flush=True)
    try:
        pipeline.run()
        torch.cuda.synchronize()
        for message in sink.get_messages():
            frame_out = message.payload().get_data()
            ids = frame_out["audit_id"].to_arrow().to_pylist()
            seen_out.update(ids)
            scores = message.tensors().get_tensor("probs").get()
            if scores.shape != (len(ids), 1):
                note("output_shape_mismatch", ids)
                continue
            for index, score in zip(ids, scores[:, 0]):
                hf_score = references[index]
                error = abs(float(score) - hf_score)
                if not np.isfinite(score) or not 0 <= score <= 1:
                    note("invalid_score", [index])
                if not np.isclose(score, hf_score, atol=1e-4, rtol=1e-4):
                    note("score_mismatch", [index])
                if (score >= 0.5) != (hf_score >= 0.5):
                    note("decision_mismatch", [index])
                comparisons.append(dict(audit_id=int(index), source=samples[index][1],
                                        hf_score=hf_score, morpheus_score=float(score), absolute_error=error))
        expected_seen = Counter(range(len(samples)))
        if seen_pre != expected_seen or seen_out != expected_seen:
            note("missing_or_duplicate_rows", [])
        result = dict(status="PASS" if not issues else "FAIL", rows=len(samples),
                      compared_rows=len(comparisons), issues=dict(Counter(issues)), first_issues=first_issues,
                      max_absolute_score_error=max((r["absolute_error"] for r in comparisons), default=None),
                      tolerance=dict(atol=1e-4, rtol=1e-4), threshold=0.5, bf16=use_bf16,
                      checkpoint=str(args.checkpoint), dataset_manifest_sha256=digest(manifest_path),
                      checkpoint_weights_sha256=digest(args.checkpoint/"model.safetensors"),
                      adapter_sha256=digest(Path(__file__).with_name("morpheus_context_inference.py")),
                      preprocessing="native body tokens + project-local CLS/SEP framing, length 256",
                      preprocessing_adapter_sha256=digest(Path(__file__).with_name("morpheus_bert_special_tokens.py")),
                      versions=dict(torch=torch.__version__, transformers=transformers.__version__,
                                    cupy=cp.__version__, cudf=cudf.__version__),
                      scope="Technical parity only; no model-quality, production-readiness or raw-event transformation claim",
                      held_out_data_used=False)
    except Exception as error:
        failure = dict(status="ERROR", error_type=type(error).__name__, error=str(error),
                       input_rows_seen=sum(seen_pre.values()), expected_rows=len(samples),
                       issues=dict(Counter(issues)), first_issues=first_issues,
                       checkpoint=str(args.checkpoint), held_out_data_used=False)
        (args.output/"parity_report.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        print(json.dumps(failure, indent=2), flush=True)
        print("Diagnostic report:", args.output/"parity_report.json", flush=True)
        raise
    (args.output/"parity_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["raw_event_check"] = raw_report
    result["raw_adapter_sha256"] = (
        digest(Path(__file__).with_name("raw_event_contract.py"))
        if raw_report is not None else None
    )
    result["text_builder_sha256"] = digest(
        Path(__file__).with_name("build_context_dataset.py")
    )
    result["scope"] = (
        "Technical parity; optional raw reconstruction recorded in "
        "raw_event_check. No production-readiness claim."
    )
    (args.output/"parity_report.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    if not issues:
        from quality_metrics import evaluate
        quality = evaluate(data["validation"], comparisons)
        (args.output/"quality_report.json").write_text(
            json.dumps(quality, indent=2), encoding="utf-8"
        )
    with (args.output/"score_comparison.jsonl").open("x", encoding="utf-8") as stream:
        for item in comparisons:
            stream.write(json.dumps(item) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    print("Saved:", args.output, flush=True)
    if issues:
        raise SystemExit("FAIL: parity differences require investigation before integration")


if __name__ == "__main__":
    main()
