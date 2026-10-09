"""Display-only behavioral replay worker. Not a malicious classifier."""

import hashlib
import json
import math
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from confluent_kafka import Consumer, Producer
from torch import nn


BROKER = "kafka:29092"
INPUT = "replay-behavioral-input"
OUTPUT = "replay-behavioral-output"
GROUP = "replay-behavioral-raw-v1"

RUNTIME = Path(
    "/models/morpheus-behavioral-v1-4-dev"
)

MANIFEST = RUNTIME / "runtime_manifest.json"


def digest(path):
    h = hashlib.sha256()

    with Path(path).open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


class AutoEncoder(nn.Module):
    def __init__(self, n_features):
        super().__init__()

        self.encoder = nn.Sequential(
            nn.Linear(n_features, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
        )

        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, n_features),
        )

    def forward(self, x):
        return self.decoder(
            self.encoder(x)
        )


def flatten(obj, prefix=""):
    out = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            name = (
                f"{prefix}.{key}"
                if prefix
                else key
            )

            out.update(
                flatten(value, name)
            )

    elif isinstance(obj, list):
        out[prefix] = ",".join(
            str(x) for x in obj
        )

    else:
        out[prefix] = obj

    return out


def present(flat, key):
    return int(
        key in flat
        and flat[key] is not None
        and str(flat[key]).strip() != ""
    )


def prefix_count(flat, prefix):
    return sum(
        1
        for key in flat
        if key.startswith(prefix)
    )


def string_length(value):
    if value is None:
        return 0

    return len(str(value))


def is_private_ip(value):
    if not value:
        return 0

    value = str(value)

    if value.startswith("10."):
        return 1

    if value.startswith("192.168."):
        return 1

    if value.startswith("127."):
        return 1

    if value.startswith("100."):
        return 1

    if value.startswith("172."):
        try:
            second = int(
                value.split(".")[1]
            )

            return int(
                16 <= second <= 31
            )

        except Exception:
            return 0

    if value == "::1":
        return 1

    return 0


def parse_hour(event):
    value = event.get("timestamp")

    if not value:
        return None

    value = str(value)

    try:
        if value.endswith("Z"):
            value = (
                value[:-1]
                + "+00:00"
            )

        if (
            len(value) >= 5
            and value[-5] in "+-"
            and value[-3] != ":"
        ):
            value = (
                value[:-5]
                + value[-5:-2]
                + ":"
                + value[-2:]
            )

        return datetime.fromisoformat(
            value
        ).hour

    except Exception:
        return None


def feature_values(event):
    flat = flatten(event)

    full_log = (
        event.get("full_log")
        or ""
    )

    command = (
        flat.get("data.command")
        or ""
    )

    srcip = flat.get(
        "data.srcip"
    )

    hour = parse_hour(event)

    if hour is None:
        has_hour = 0
        hour_sin = 0.0
        hour_cos = 0.0

    else:
        angle = (
            2 * math.pi
            * hour / 24.0
        )

        has_hour = 1
        hour_sin = math.sin(angle)
        hour_cos = math.cos(angle)

    return {
        "has_full_log":
            int(bool(full_log)),

        "has_command":
            present(flat, "data.command"),

        "has_srcip":
            present(flat, "data.srcip"),

        "srcip_private":
            is_private_ip(srcip),

        "has_srcuser":
            present(flat, "data.srcuser"),

        "has_dstuser":
            present(flat, "data.dstuser"),

        "has_package":
            present(flat, "data.package"),

        "has_dpkg_status":
            present(flat, "data.dpkg_status"),

        "has_sca_check":
            int(any(
                k.startswith("data.sca.check.")
                for k in flat
            )),

        "has_sca_summary":
            int(
                any(
                    k.startswith("data.sca.")
                    for k in flat
                )
                and not any(
                    k.startswith(
                        "data.sca.check."
                    )
                    for k in flat
                )
            ),

        "has_vulnerability":
            int(any(
                k.startswith(
                    "data.vulnerability."
                )
                for k in flat
            )),

        "has_syscheck":
            int(any(
                k.startswith("syscheck.")
                for k in flat
            )),

        "has_tty":
            present(flat, "data.tty"),

        "has_pwd":
            present(flat, "data.pwd"),

        "has_previous_log":
            present(flat, "previous_log"),

        "has_previous_output":
            present(flat, "previous_output"),

        "full_log_length":
            min(
                string_length(full_log),
                4096,
            ) / 4096.0,

        "command_length":
            min(
                string_length(command),
                1024,
            ) / 1024.0,

        "data_field_count":
            min(
                prefix_count(
                    flat,
                    "data.",
                ),
                100,
            ) / 100.0,

        "sca_field_count":
            min(
                prefix_count(
                    flat,
                    "data.sca.",
                ),
                100,
            ) / 100.0,

        "vuln_field_count":
            min(
                prefix_count(
                    flat,
                    "data.vulnerability.",
                ),
                100,
            ) / 100.0,

        "syscheck_field_count":
            min(
                prefix_count(
                    flat,
                    "syscheck.",
                ),
                100,
            ) / 100.0,

        "has_hour":
            has_hour,

        "hour_sin":
            hour_sin,

        "hour_cos":
            hour_cos,
    }


def command_class(command):
    command = (
        command or ""
    ).strip()

    if not command:
        return "missing"

    try:
        tokens = shlex.split(
            command
        )

    except Exception:
        tokens = command.split()

    if not tokens:
        return "missing"

    base = Path(
        tokens[0]
    ).name.lower()

    rest = [
        x.lower()
        for x in tokens[1:]
    ]

    if base in {
        "apt",
        "apt-get",
    }:
        if any(
            x in {
                "remove",
                "purge",
                "autoremove",
            }
            for x in rest
        ):
            return "apt_remove"

        if "install" in rest:
            return "apt_install"

        if "update" in rest:
            return "apt_update"

        if any(
            x in {
                "upgrade",
                "dist-upgrade",
                "full-upgrade",
            }
            for x in rest
        ):
            return "apt_upgrade"

        return "apt_other"

    if base in {
        "bash",
        "sh",
        "zsh",
        "dash",
    }:
        return "shell"

    if base.endswith(".sh"):
        return "script"

    mappings = {
        "systemctl": "systemctl",
        "docker": "docker",
        "docker-compose": "docker",
        "rm": "file_remove",
        "unlink": "file_remove",

        "useradd": "user_management",
        "usermod": "user_management",
        "userdel": "user_management",

        "groupadd": "group_management",
        "groupmod": "group_management",
        "groupdel": "group_management",
    }

    return mappings.get(
        base,
        base,
    )


def package_count(command):
    command = (
        command or ""
    ).strip()

    try:
        tokens = shlex.split(command)

    except Exception:
        tokens = command.split()

    if not tokens:
        return 0

    base = Path(
        tokens[0]
    ).name.lower()

    if base not in {
        "apt",
        "apt-get",
    }:
        return 0

    operation_index = None

    for i, token in enumerate(
        tokens[1:],
        1,
    ):
        if token.lower() in {
            "install",
            "remove",
            "purge",
            "autoremove",
        }:
            operation_index = i
            break

    if operation_index is None:
        return 0

    return sum(
        1
        for token
        in tokens[
            operation_index + 1:
        ]
        if not token.startswith("-")
    )


def routing_status(
    support,
):
    if support >= 50:
        return "local_model"

    if support >= 20:
        return "fallback_supported"

    if support > 0:
        return "limited_history"

    return "novel_cohort"


def load_runtime():
    manifest = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    if (
        manifest.get(
            "schema_version"
        )
        !=
        "morpheus-behavioral-runtime-1"
    ):
        raise ValueError(
            "Unexpected runtime schema"
        )

    if (
        manifest.get("model_version")
        != "behavioral-v1.4"
    ):
        raise ValueError(
            "Unexpected model version"
        )

    if (
        manifest.get(
            "production_ready"
        )
        is not False
    ):
        raise ValueError(
            "Expected development runtime"
        )

    if (
        manifest.get(
            "automated_response_allowed"
        )
        is not False
    ):
        raise ValueError(
            "Automated response must be disabled"
        )

    cohort_support = {
        (
            item["decoder"],
            item["location"],
        ):
        int(item["count"])

        for item
        in manifest["cohort_support"]
    }

    semantic_support = {
        (
            item["decoder"],
            item["location"],
            item["command_class"],
        ):
        int(item["count"])

        for item
        in manifest["semantic_support"]
    }

    runtime_cohorts = {
        (
            item["decoder"],
            item["location"],
        ):
        item

        for item
        in manifest["runtime_cohorts"]
    }

    models = {}

    for key, cfg in (
        runtime_cohorts.items()
    ):
        if not cfg.get(
            "runtime_enabled"
        ):
            continue

        model_file = cfg.get(
            "model_file"
        )

        if not model_file:
            raise ValueError(
                f"Enabled model missing file: {key}"
            )

        path = (
            RUNTIME
            / "models"
            / model_file
        )

        expected_hash = cfg.get(
            "model_sha256"
        )

        actual_hash = digest(path)

        if (
            not expected_hash
            or actual_hash
            != expected_hash
        ):
            raise ValueError(
                f"Model hash mismatch: {key}"
            )

        saved = torch.load(
            path,
            map_location="cpu",
            weights_only=False,
        )

        names = saved[
            "feature_names"
        ]

        model = AutoEncoder(
            len(names)
        )

        model.load_state_dict(
            saved["state_dict"]
        )

        model.eval()

        models[key] = {
            "model":
                model,

            "features":
                names,

            "mean":
                np.asarray(
                    saved["mean"],
                    dtype=np.float32,
                ),

            "std":
                np.asarray(
                    saved["std"],
                    dtype=np.float32,
                ),

            "threshold":
                float(
                    saved["threshold"]
                ),

            "model_sha256":
                actual_hash,
        }

    return (
        manifest,
        cohort_support,
        semantic_support,
        runtime_cohorts,
        models,
    )


def score_model(
    spec,
    features,
):
    raw = np.asarray(
        [
            float(features[name])
            for name
            in spec["features"]
        ],
        dtype=np.float32,
    )

    x_np = (
        raw - spec["mean"]
    ) / spec["std"]

    x = torch.tensor(
        x_np,
        dtype=torch.float32,
    ).unsqueeze(0)

    with torch.no_grad():
        reconstructed = (
            spec["model"](x)
            .squeeze(0)
            .numpy()
        )

    error = float(
        np.mean(
            (
                reconstructed
                - x_np
            ) ** 2
        )
    )

    threshold = spec[
        "threshold"
    ]

    return (
        error,
        threshold,
        error / max(
            threshold,
            1e-12,
        ),
        error > threshold,
    )


def main():
    (
        manifest,
        cohort_support,
        semantic_support,
        runtime_cohorts,
        models,
    ) = load_runtime()

    manifest_hash = digest(
        MANIFEST
    )

    consumer = Consumer({
        "bootstrap.servers":
            BROKER,

        "group.id":
            GROUP,

        "enable.auto.commit":
            False,

        "enable.auto.offset.store":
            False,

        "auto.offset.reset":
            "earliest",
    })

    producer = Producer({
        "bootstrap.servers":
            BROKER,

        "enable.idempotence":
            True,

        "acks":
            "all",

        "delivery.timeout.ms":
            30000,
    })

    try:
        consumer.subscribe(
            [INPUT]
        )

        message = None

        deadline = (
            time.monotonic()
            + 30
        )

        while (
            time.monotonic()
            < deadline
        ):
            item = consumer.poll(1)

            if item is None:
                continue

            if item.error():
                raise RuntimeError(
                    "Kafka input error"
                )

            message = item
            break

        if message is None:
            raise RuntimeError(
                "No replay event received"
            )

        raw = json.loads(
            message.value()
        )

        if not isinstance(raw, dict):
            raise ValueError(
                "Expected raw Wazuh event"
            )

        identity = [
            raw["manager"]["name"],
            raw["agent"]["id"],
            raw["id"],
        ]

        if any(
            not isinstance(
                value,
                (str, int),
            )
            or isinstance(
                value,
                bool,
            )
            or not str(value).strip()

            for value in identity
        ):
            raise ValueError(
                "Invalid event identity"
            )

        uid = hashlib.sha256(
            json.dumps(
                [
                    str(value)
                    for value
                    in identity
                ]
            ).encode()
        ).hexdigest()

        if (
            message.key() is not None
            and message.key() != uid.encode()
        ):
            raise ValueError(
                "Raw replay Kafka key mismatch"
            )

        decoder = str(
            raw.get(
                "decoder",
                {},
            ).get(
                "name",
                "[missing]",
            )
        )

        location = str(
            raw.get(
                "location",
                "[missing]",
            )
        )

        key = (
            decoder,
            location,
        )

        train_support = (
            cohort_support.get(
                key,
                0,
            )
        )

        routing = routing_status(
            train_support
        )

        command = (
            raw.get(
                "data",
                {},
            ).get(
                "command"
            )
        )

        command_cls = (
            command_class(
                command
            )
        )

        semantic_count = (
            semantic_support.get(
                (
                    decoder,
                    location,
                    command_cls,
                ),
                0,
            )
        )

        semantic_novelty = (
            semantic_count == 0
        )

        ae_error = None
        ae_threshold = None
        ae_ratio = None
        ae_anomaly = None
        model_hash = None

        if routing == "local_model":

            cfg = runtime_cohorts.get(
                key
            )

            if cfg is None:
                raise RuntimeError(
                    "Local cohort missing runtime policy"
                )

            if cfg.get(
                "runtime_enabled"
            ):
                spec = models[key]

                features = (
                    feature_values(
                        raw
                    )
                )

                (
                    ae_error,
                    ae_threshold,
                    ae_ratio,
                    ae_anomaly,
                ) = score_model(
                    spec,
                    features,
                )

                model_hash = (
                    spec[
                        "model_sha256"
                    ]
                )

                if (
                    ae_anomaly
                    and semantic_novelty
                ):
                    state = (
                        "behavioral_anomaly"
                        "+semantic_novelty"
                    )

                elif ae_anomaly:
                    state = (
                        "behavioral_anomaly"
                    )

                elif semantic_novelty:
                    state = (
                        "semantic_novelty"
                    )

                else:
                    state = (
                        "baseline_consistent"
                    )

            else:
                state = cfg[
                    "runtime_reason"
                ]

        else:
            state = routing

        rule = raw.get(
            "rule",
            {},
        )

        output = {
            "schema_version":
                "replay-behavioral-1",

            "event_uid":
                uid,

            "source_type":
                "wazuh",

            "processing_mode":
                "replay",

            "model_version":
                "behavioral-v1.4",

            "analysis_state":
                state,

            "routing_status":
                routing,

            "train_cohort_support":
                train_support,

            "ae_reconstruction_error":
                ae_error,

            "ae_threshold":
                ae_threshold,

            "ae_ratio":
                ae_ratio,

            "ae_anomaly":
                ae_anomaly,

            "semantic_novelty":
                semantic_novelty,

            "command_class":
                command_cls,

            "command_class_train_support":
                semantic_count,

            "package_argument_count":
                package_count(command),

            "wazuh_rule_id":
                rule.get("id"),

            "wazuh_rule_level":
                rule.get("level"),

            "scored_at_utc":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "runtime_manifest_sha256":
                manifest_hash,

            "model_sha256":
                model_hash,

            "input_partition":
                message.partition(),

            "input_offset":
                message.offset(),

            "production_ready":
                False,

            "automated_response_allowed":
                False,
        }

        delivered = []

        producer.produce(
            OUTPUT,
            key=uid.encode(),
            value=json.dumps(
                output,
                allow_nan=False,
            ).encode(),
            on_delivery=lambda error, msg:
                delivered.append(error),
        )

        remaining = producer.flush(
            35
        )

        if (
            remaining
            or len(delivered) != 1
            or delivered[0]
            is not None
        ):
            raise RuntimeError(
                "Behavioral output delivery failed"
            )

        consumer.commit(
            message=message,
            asynchronous=False,
        )

        print(
            "Behavioral replay: PASS",
            flush=True,
        )

        print(
            "event_uid:",
            uid,
            flush=True,
        )

        print(
            "analysis_state:",
            state,
            flush=True,
        )

        print(
            "routing_status:",
            routing,
            flush=True,
        )

        print(
            "ae_ratio:",
            ae_ratio,
            flush=True,
        )

        print(
            "semantic_novelty:",
            semantic_novelty,
            flush=True,
        )

    finally:
        consumer.close()


if __name__ == "__main__":
    main()
