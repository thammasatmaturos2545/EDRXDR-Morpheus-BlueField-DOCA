#!/usr/bin/env bash
set -euo pipefail
# Run on the reserved H100 host from ~/EDRXDR-Morpheus.
# Copy this training directory into that repository first.
mode="${1:-smoke}"
case "$mode" in
  smoke) options=(--smoke) ;;
  train) options=(--epochs 1) ;;
  *) echo 'Usage: bash training/run_training.sh [smoke|train]' >&2; exit 2 ;;
esac
for volume in edrxdr-hf-cache edrxdr-model-output; do
  docker volume inspect "$volume" >/dev/null
done
run="wazuh-severity-nlp-v1-${mode}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
docker run --rm --pull never --network none \
  --gpus '"device=0"' --shm-size 1g \
  --mount type=bind,src="$PWD/training",dst=/scripts,readonly \
  --mount type=bind,src="$PWD/morpheus/data",dst=/data,readonly \
  --mount type=volume,src=edrxdr-hf-cache,dst=/hf-cache \
  --mount type=volume,src=edrxdr-model-output,dst=/model-output \
  --tmpfs /tmp:rw,size=1g \
  -e HF_HOME=/hf-cache -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  --entrypoint /opt/conda/envs/morpheus/bin/python \
  edrxdr-morpheus-train:25.06 /scripts/train_wazuh_severity.py \
  --output-dir "/model-output/$run" "${options[@]}" \
  --text-key "${TEXT_KEY:-text}" --label-key "${LABEL_KEY:-label}" \
  --group-key "${GROUP_KEY:-rule_id}"
