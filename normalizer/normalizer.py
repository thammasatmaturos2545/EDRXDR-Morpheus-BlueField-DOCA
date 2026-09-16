import json
import time
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable


# ============================================================
# CONFIG
# ============================================================

KAFKA_BROKER = "kafka:29092"

BLUEFIELD_TOPIC = "bluefield-events"
WAZUH_TOPIC = "wazuh-alerts"

OUTPUT_TOPIC = "morpheus-input"

CONSUMER_GROUP = "edrxdr-normalizer-v2"


# ============================================================
# KAFKA
# ============================================================

def connect_consumer():
    while True:
        try:
            print(
                f"Connecting Kafka consumer to "
                f"{KAFKA_BROKER}..."
            )

            consumer = KafkaConsumer(
                BLUEFIELD_TOPIC,
                WAZUH_TOPIC,

                bootstrap_servers=[
                    KAFKA_BROKER
                ],

                group_id=CONSUMER_GROUP,

                auto_offset_reset="latest",

                enable_auto_commit=True,

                value_deserializer=lambda data: (
                    json.loads(
                        data.decode("utf-8")
                    )
                ),
            )

            print("✅ Kafka Consumer connected")
            return consumer

        except NoBrokersAvailable:
            print(
                "Kafka unavailable. "
                "Retrying in 5 seconds..."
            )
            time.sleep(5)


def connect_producer():
    while True:
        try:
            print(
                f"Connecting Kafka producer to "
                f"{KAFKA_BROKER}..."
            )

            producer = KafkaProducer(
                bootstrap_servers=[
                    KAFKA_BROKER
                ],

                value_serializer=lambda value: (
                    json.dumps(
                        value,
                        ensure_ascii=False
                    ).encode("utf-8")
                ),

                acks="all",
                retries=5,
            )

            print("✅ Kafka Producer connected")
            return producer

        except NoBrokersAvailable:
            print(
                "Kafka unavailable. "
                "Retrying in 5 seconds..."
            )
            time.sleep(5)


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# BLUEFIELD NORMALIZATION
# ============================================================

bluefield_previous = {}


def normalize_bluefield(event):
    """
    Normalize NVIDIA BlueField / DOCA telemetry.
    """

    interface = event.get(
        "interface",
        "unknown"
    )

    rx_packets = safe_int(
        event.get("rx_packets")
    )

    tx_packets = safe_int(
        event.get("tx_packets")
    )

    rx_bytes = safe_int(
        event.get("rx_bytes")
    )

    tx_bytes = safe_int(
        event.get("tx_bytes")
    )

    previous = bluefield_previous.get(
        interface,
        {}
    )

    delta_rx_packets = max(
        0,
        rx_packets
        - safe_int(
            previous.get("rx_packets")
        )
    )

    delta_tx_packets = max(
        0,
        tx_packets
        - safe_int(
            previous.get("tx_packets")
        )
    )

    delta_rx_bytes = max(
        0,
        rx_bytes
        - safe_int(
            previous.get("rx_bytes")
        )
    )

    delta_tx_bytes = max(
        0,
        tx_bytes
        - safe_int(
            previous.get("tx_bytes")
        )
    )

    bluefield_previous[
        interface
    ] = {
        "rx_packets": rx_packets,
        "tx_packets": tx_packets,
        "rx_bytes": rx_bytes,
        "tx_bytes": tx_bytes,
    }

    normalized = {
        "timestamp": event.get(
            "timestamp",
            utc_now()
        ),

        "event_type":
            "network_telemetry",

        "source_type":
            "bluefield",

        "source_product":
            "nvidia-bluefield-3",

        "pipeline_source":
            "bluefield-events",

        "sensor":
            "nvidia-bluefield-3",

        "ibdev": event.get(
            "ibdev",
            "unknown"
        ),

        "interface": interface,

        "rx_packets":
            rx_packets,

        "tx_packets":
            tx_packets,

        "rx_bytes":
            rx_bytes,

        "tx_bytes":
            tx_bytes,

        "delta_rx_packets":
            delta_rx_packets,

        "delta_tx_packets":
            delta_tx_packets,

        "delta_rx_bytes":
            delta_rx_bytes,

        "delta_tx_bytes":
            delta_tx_bytes,

        "rx_errors": safe_int(
            event.get("rx_errors")
        ),

        "tx_errors": safe_int(
            event.get("tx_errors")
        ),

        # Keep original event for
        # future Morpheus enrichment.
        "raw_event": event,
    }

    return normalized


# ============================================================
# WAZUH NORMALIZATION
# ============================================================

def normalize_wazuh(event):
    """
    Normalize Wazuh alerts into the common EDRXDR schema.
    """

    rule = event.get(
        "rule",
        {}
    )

    agent = event.get(
        "agent",
        {}
    )

    manager = event.get(
        "manager",
        {}
    )

    decoder = event.get(
        "decoder",
        {}
    )

    data = event.get(
        "data",
        {}
    )

    mitre = rule.get(
        "mitre",
        {}
    )

    groups = rule.get(
        "groups",
        []
    )

    normalized = {
        "timestamp": event.get(
            "timestamp",
            utc_now()
        ),

        "event_type":
            "endpoint_security_alert",

        "source_type":
            "wazuh",

        "source_product":
            "wazuh",

        "pipeline_source":
            "wazuh-alerts",

        # ------------------------
        # Wazuh Rule
        # ------------------------

        "rule_id": str(
            rule.get(
                "id",
                "unknown"
            )
        ),

        "rule_level": safe_int(
            rule.get("level")
        ),

        "rule_description":
            rule.get(
                "description",
                ""
            ),

        "rule_groups":
            groups,

        "rule_firedtimes":
            safe_int(
                rule.get(
                    "firedtimes"
                )
            ),

        # ------------------------
        # Endpoint / Agent
        # ------------------------

        "agent_id":
            agent.get(
                "id",
                "unknown"
            ),

        "agent_name":
            agent.get(
                "name",
                "unknown"
            ),

        "agent_ip":
            agent.get(
                "ip",
                ""
            ),

        "manager_name":
            manager.get(
                "name",
                ""
            ),

        # ------------------------
        # MITRE ATT&CK
        # ------------------------

        "mitre_id":
            mitre.get(
                "id",
                []
            ),

        "mitre_tactic":
            mitre.get(
                "tactic",
                []
            ),

        "mitre_technique":
            mitre.get(
                "technique",
                []
            ),

        # ------------------------
        # Detection metadata
        # ------------------------

        "decoder_name":
            decoder.get(
                "name",
                ""
            ),

        "location":
            event.get(
                "location",
                ""
            ),

        "full_log":
            event.get(
                "full_log",
                ""
            ),

        "event_id":
            event.get(
                "id",
                ""
            ),

        "src_user":
            data.get(
                "srcuser",
                ""
            ),

        "dst_user":
            data.get(
                "dstuser",
                ""
            ),

        "src_ip":
            data.get(
                "srcip",
                ""
            ),

        "dst_ip":
            data.get(
                "dstip",
                ""
            ),

        # Keep complete original Wazuh alert.
        "raw_event":
            event,
    }

    return normalized


# ============================================================
# ROUTER
# ============================================================

def normalize_event(
    topic,
    event
):
    if topic == BLUEFIELD_TOPIC:
        return normalize_bluefield(
            event
        )

    if topic == WAZUH_TOPIC:
        return normalize_wazuh(
            event
        )

    return None


# ============================================================
# START
# ============================================================

print(
    "======================================"
)

print(
    " EDRXDR Multi-Source Event Normalizer"
)

print(
    "======================================"
)

print(
    f"Input 1 : {BLUEFIELD_TOPIC}"
)

print(
    f"Input 2 : {WAZUH_TOPIC}"
)

print(
    f"Output  : {OUTPUT_TOPIC}"
)

print("")

consumer = connect_consumer()
producer = connect_producer()

print("")
print(
    "✅ Multi-source Normalizer started"
)

print(
    "Waiting for BlueField + Wazuh events..."
)

print("")


# ============================================================
# MAIN LOOP
# ============================================================

for message in consumer:

    try:
        source_topic = (
            message.topic
        )

        input_event = (
            message.value
        )

        normalized = normalize_event(
            source_topic,
            input_event
        )

        if normalized is None:
            print(
                f"⚠️ Unsupported topic: "
                f"{source_topic}"
            )
            continue

        producer.send(
            OUTPUT_TOPIC,
            value=normalized
        )

        producer.flush()

        if (
            normalized["source_type"]
            == "wazuh"
        ):
            print(
                "[WAZUH → MORPHEUS] "
                f"level="
                f"{normalized['rule_level']} "
                f"rule="
                f"{normalized['rule_id']} "
                f"agent="
                f"{normalized['agent_name']} "
                f"description="
                f"{normalized['rule_description']}"
            )

        elif (
            normalized["source_type"]
            == "bluefield"
        ):
            print(
                "[BLUEFIELD → MORPHEUS] "
                f"device="
                f"{normalized['ibdev']} "
                f"interface="
                f"{normalized['interface']} "
                f"rx="
                f"{normalized['rx_packets']} "
                f"tx="
                f"{normalized['tx_packets']}"
            )

    except Exception as error:
        print(
            f"❌ Normalizer error: "
            f"{error}"
        )
