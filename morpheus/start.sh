#!/bin/bash
set -e

echo "======================================"
echo " EDRXDR NVIDIA Morpheus Pipeline"
echo "======================================"
echo "Input  : morpheus-input"
echo "Output : morpheus-output"

morpheus --log_level=INFO \
  run pipeline-other \
  from-kafka \
    --bootstrap_servers kafka:29092 \
    --input_topic morpheus-input \
  deserialize \
  monitor \
    --description "EDRXDR Morpheus Events" \
  serialize \
  to-kafka \
    --bootstrap_servers kafka:29092 \
    --output_topic morpheus-output
