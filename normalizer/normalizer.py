import json
import time
from kafka import KafkaConsumer, KafkaProducer


KAFKA_BROKER = "kafka:29092"

INPUT_TOPIC = "bluefield-events"
OUTPUT_TOPIC = "morpheus-input"


print("======================================")
print(" EDRXDR Event Normalizer")
print("======================================")
print(f"Input  : {INPUT_TOPIC}")
print(f"Output : {OUTPUT_TOPIC}")


consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="edrxdr-normalizer",
    value_deserializer=lambda x: json.loads(
        x.decode("utf-8")
    ),
)


producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda x: json.dumps(
        x
    ).encode("utf-8"),
    acks="all",
)


previous = {}


def normalize_bluefield(event):

    device = event.get("ibdev", "unknown")

    rx_packets = int(event.get("rx_packets", 0))
    tx_packets = int(event.get("tx_packets", 0))

    rx_bytes = int(event.get("rx_bytes", 0))
    tx_bytes = int(event.get("tx_bytes", 0))

    rx_errors = int(event.get("rx_errors", 0))
    tx_errors = int(event.get("tx_errors", 0))


    old = previous.get(device)


    # First event from this device
    if old is None:

        delta_rx_packets = 0
        delta_tx_packets = 0

        delta_rx_bytes = 0
        delta_tx_bytes = 0

    else:

        delta_rx_packets = max(
            0,
            rx_packets - old["rx_packets"]
        )

        delta_tx_packets = max(
            0,
            tx_packets - old["tx_packets"]
        )

        delta_rx_bytes = max(
            0,
            rx_bytes - old["rx_bytes"]
        )

        delta_tx_bytes = max(
            0,
            tx_bytes - old["tx_bytes"]
        )


    previous[device] = {
        "rx_packets": rx_packets,
        "tx_packets": tx_packets,
        "rx_bytes": rx_bytes,
        "tx_bytes": tx_bytes,
    }


    normalized = {

        "timestamp":
            event.get("timestamp"),

        "event_type":
            "network_telemetry",

        "source_type":
            "bluefield",

        "sensor":
            "nvidia-bluefield-3",

        "ibdev":
            device,

        "interface":
            event.get(
                "interface",
                "unknown"
            ),

        # Current counters
        "rx_packets":
            rx_packets,

        "tx_packets":
            tx_packets,

        "rx_bytes":
            rx_bytes,

        "tx_bytes":
            tx_bytes,

        # Delta between samples
        "delta_rx_packets":
            delta_rx_packets,

        "delta_tx_packets":
            delta_tx_packets,

        "delta_rx_bytes":
            delta_rx_bytes,

        "delta_tx_bytes":
            delta_tx_bytes,

        "rx_errors":
            rx_errors,

        "tx_errors":
            tx_errors,

        # Will later be filled by Morpheus
        "threat_score":
            0.0,

        "threat_class":
            "unknown",
    }


    return normalized


print("\n✅ Normalizer started")
print("Waiting for BlueField events...\n")


for message in consumer:

    try:

        event = message.value

        if event.get("source") != "bluefield":
            continue


        normalized = normalize_bluefield(
            event
        )


        producer.send(
            OUTPUT_TOPIC,
            normalized
        )


        producer.flush()


        print(
            "[NORMALIZED]",
            json.dumps(
                normalized,
                indent=None
            )
        )


    except Exception as error:

        print(
            f"[ERROR] {error}"
        )

        time.sleep(1)
