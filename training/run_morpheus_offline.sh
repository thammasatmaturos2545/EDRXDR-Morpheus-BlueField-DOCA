#!/usr/bin/env bash
set -euo pipefail
run="morpheus-offline-check-$(date -u +%Y%m%dT%H%M%SZ)-$$"
for volume in edrxdr-dataset edrxdr-model-output; do
  docker volume inspect "$volume" >/dev/null
done
docker run --rm --pull never --network none \
  --gpus '"device=0"' --cpus 4 --memory 16g --shm-size 1g \
  --mount type=bind,src="$PWD/training",dst=/scripts,readonly \
  --mount type=volume,src=edrxdr-dataset,dst=/dataset,readonly \
  --mount type=volume,src=edrxdr-model-output,dst=/models,readonly \
  --mount type=volume,src=edrxdr-model-output,dst=/results \
  --tmpfs /tmp:rw,size=1g \
  -e HF_HOME=/tmp/hf-cache -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e TOKENIZERS_PARALLELISM=false -e OMP_NUM_THREADS=4 \
  --entrypoint /opt/conda/envs/morpheus/bin/python \
  edrxdr-morpheus-train:25.06 -B /scripts/check_morpheus_offline.py \
  --checkpoint /models/wazuh-severity-context-v2-balanced-20261008T190719Z-1398863 \
  --dataset /dataset/wazuh-context-v2-20261008T185539Z-1179365 \
  --output "/results/$run"
