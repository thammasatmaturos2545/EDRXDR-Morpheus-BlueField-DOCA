import json
import os
import time

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


KAFKA_BROKER = "kafka:29092"
KAFKA_TOPIC = "wazuh-alerts"

ALERT_FILE = "/var/ossec/logs/alerts/alerts.json"


def connect_kafka():
    while True:
        try:
            print(
                f"Connecting to Kafka: {KAFKA_BROKER}"
            )

            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda value: json.dumps(
                    value,
                    ensure_ascii=False
                ).encode("utf-8"),
                acks="all",
                retries=5,
            )

            print("✅ Kafka connected")
            return producer

        except NoBrokersAvailable:
            print("Kafka not ready. Retrying in 5 seconds...")
            time.sleep(5)


def wait_for_alert_file():
    while not os.path.exists(ALERT_FILE):
        print(
            f"Waiting for {ALERT_FILE}..."
        )
        time.sleep(5)


def open_alert_file():
    wait_for_alert_file()

    file_handle = open(
        ALERT_FILE,
        "r",
        encoding="utf-8",
        errors="replace",
    )

    # Start at the end.
    # Only forward new Wazuh alerts.
    file_handle.seek(0, os.SEEK_END)

    stat = os.stat(ALERT_FILE)

    return file_handle, stat.st_ino


producer = connect_kafka()

file_handle, current_inode = open_alert_file()

print("======================================")
print(" EDRXDR Wazuh Kafka Forwarder")
print("======================================")
print(f"Source : {ALERT_FILE}")
print(f"Kafka  : {KAFKA_TOPIC}")
print("")
print("✅ Waiting for new Wazuh alerts...")


while True:
    try:
        line = file_handle.readline()

        if not line:
            time.sleep(0.5)

            # Handle Wazuh log rotation
            try:
                stat = os.stat(ALERT_FILE)

                if (
                    stat.st_ino != current_inode
                    or stat.st_size < file_handle.tell()
                ):
                    print(
                        "Wazuh alerts.json rotated. "
                        "Reopening file..."
                    )

                    file_handle.close()

                    file_handle, current_inode = (
                        open_alert_file()
                    )

            except FileNotFoundError:
                pass

            continue

        line = line.strip()

        if not line:
            continue

        try:
            alert = json.loads(line)

        except json.JSONDecodeError as error:
            print(
                f"⚠️ Invalid Wazuh JSON skipped: {error}"
            )
            continue

        rule = alert.get("rule", {})
        agent = alert.get("agent", {})

        producer.send(
            KAFKA_TOPIC,
            value=alert,
        )

        producer.flush()

        print(
            "[WAZUH → KAFKA] "
            f"rule={rule.get('id', 'unknown')} "
            f"level={rule.get('level', 0)} "
            f"agent={agent.get('name', 'unknown')} "
            f"description={rule.get('description', '')}"
        )

    except Exception as error:
        print(
            f"❌ Forwarder error: {error}"
        )

        time.sleep(2)

        try:
            producer = connect_kafka()
        except Exception:
            pass
