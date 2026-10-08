#!/usr/bin/env bash
set -euo pipefail
dataset_name="${1:?Usage: bash training/run_context_v2.sh DATASET_DIRECTORY_NAME [smoke|train|balanced]}"
mode="${2:-smoke}"
[[ "$dataset_name" =~ ^wazuh-context-v2-[A-Za-z0-9-]+$ ]] || { echo 'Invalid dataset directory name' >&2; exit 2; }
case "$mode" in
  smoke) options=(--smoke) ;;
  train) options=() ;;
  balanced) options=(--rule-balanced-loss) ;;
  *) echo 'Mode must be smoke, train or balanced' >&2; exit 2 ;;
esac
for volume in edrxdr-dataset edrxdr-hf-cache edrxdr-model-output; do
  docker volume inspect "$volume" >/dev/null
done
run="wazuh-severity-context-v2-${mode}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
docker run --rm --pull never --network none \
  --gpus '"device=0"' --cpus 4 --memory 12g --shm-size 1g \
  --mount type=bind,src="$PWD/training",dst=/scripts,readonly \
  --mount type=volume,src=edrxdr-dataset,dst=/dataset,readonly \
  --mount type=volume,src=edrxdr-hf-cache,dst=/hf-cache,readonly \
  --mount type=volume,src=edrxdr-model-output,dst=/model-output \
  --tmpfs /tmp:rw,size=1g \
  -e HF_HOME=/hf-cache -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false -e OMP_NUM_THREADS=4 \
  --entrypoint /opt/conda/envs/morpheus/bin/python \
  edrxdr-morpheus-train:25.06 -B /scripts/train_context_v2.py \
  --data-dir "/dataset/$dataset_name" --output-dir "/model-output/$run" \
  --experimental-data "${options[@]}"
