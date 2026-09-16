import json
import time
from datetime import datetime

import requests
from kafka import KafkaConsumer


KAFKA_BROKER = "kafka:29092"
INPUT_TOPIC = "morpheus-output"

OPENSEARCH_URL = "http://opensearch:9200"


print("======================================")
print(" EDRXDR OpenSearch Indexer")
print("======================================")
print(f"Kafka topic : {INPUT_TOPIC}")
print(f"OpenSearch  : {OPENSEARCH_URL}")


# -----------------------------
# Wait for OpenSearch
# -----------------------------

while True:
    try:
        response = requests.get(
            OPENSEARCH_URL,
            timeout=5
        )

        if response.status_code == 200:
            print("✅ OpenSearch connected")
            break

    except Exception:
        pass

    print("Waiting for OpenSearch...")
    time.sleep(5)


# -----------------------------
# Connect Kafka
# -----------------------------

while True:
    try:
        consumer = KafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id="edrxdr-indexer",
            value_deserializer=lambda x: x.decode("utf-8")
        )

        print("✅ Kafka connected")
        break

    except Exception as error:
        print(f"Waiting for Kafka: {error}")
        time.sleep(5)


print("\nWaiting for Morpheus output...\n")


# -----------------------------
# Main loop
# -----------------------------

for message in consumer:

    try:
        raw_message = message.value

        # Convert Kafka message -> JSON
        try:
            event = json.loads(raw_message)

        except json.JSONDecodeError as error:
            print(
                f"⚠️ Invalid JSON skipped: "
                f"{raw_message!r} ({error})"
            )
            continue

        current_date = datetime.utcnow().strftime(
            "%Y.%m.%d"
        )

        index_name = (
            f"edrxdr-events-{current_date}"
        )

        url = (
            f"{OPENSEARCH_URL}/"
            f"{index_name}/_doc"
        )

        response = requests.post(
            url,
            json=event,
            timeout=10
        )

        if response.status_code in (200, 201):

            print(
                f"✅ Indexed event -> {index_name}"
            )

            print(
                json.dumps(
                    event,
                    indent=2
                )
            )

        else:

            print(
                f"❌ OpenSearch error: "
                f"{response.status_code}"
            )

            print(
                response.text
            )

    except Exception as error:

        print(
            f"❌ Indexer error: {error}"
        )
