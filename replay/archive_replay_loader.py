"""Replay one archived raw Wazuh event into isolated replay topics."""

import gzip
import hashlib
import json
import os
import re
from pathlib import Path

from kafka import KafkaProducer


BROKER = "kafka:29092"

SEVERITY_TOPIC = "replay-wazuh-alerts"
BEHAVIORAL_TOPIC = "replay-behavioral-input"

ARCHIVE_ROOT = Path(
    "/dataset/wazuh-history-20261008T184838Z-1179365"
)

SOURCE_RE = re.compile(
    r"^\d{4}/[A-Za-z]{3}/ossec-alerts-\d{2}\.json\.gz$"
)


def load_event(relative, line_number):
    if not SOURCE_RE.fullmatch(relative):
        raise ValueError("Invalid archive path")

    if line_number < 1:
        raise ValueError("Invalid source line")

    path = ARCHIVE_ROOT / relative

    if not path.exists():
        raise FileNotFoundError(path)

    with gzip.open(
        path,
        "rt",
        encoding="utf-8",
    ) as stream:

        for current, line in enumerate(stream, 1):
            if current == line_number:
                event = json.loads(line)

                if not isinstance(event, dict):
                    raise ValueError(
                        "Expected Wazuh object"
                    )

                return event

    raise ValueError("Source line not found")


def event_uid(event):
    identity = [
        event["manager"]["name"],
        event["agent"]["id"],
        event["id"],
    ]

    if any(
        not isinstance(value, (str, int))
        or isinstance(value, bool)
        or not str(value).strip()
        for value in identity
    ):
        raise ValueError(
            "Invalid event identity"
        )

    identity = [
        str(value)
        for value in identity
    ]

    return hashlib.sha256(
        json.dumps(identity).encode()
    ).hexdigest()


def main():
    relative = os.environ[
        "REPLAY_SOURCE_FILE"
    ]

    line_number = int(
        os.environ[
            "REPLAY_SOURCE_LINE"
        ]
    )

    event = load_event(
        relative,
        line_number,
    )

    uid = event_uid(event)

    producer = KafkaProducer(
        bootstrap_servers=[BROKER],

        acks="all",
        retries=5,

        max_in_flight_requests_per_connection=1,

        value_serializer=lambda value:
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8"),
    )

    try:
        payloads = []

        for topic in (
            SEVERITY_TOPIC,
            BEHAVIORAL_TOPIC,
        ):
            result = producer.send(
                topic,
                key=uid.encode(),
                value=event,
            ).get(timeout=30)

            payloads.append(
                (
                    topic,
                    result.partition,
                    result.offset,
                )
            )

        producer.flush()

    finally:
        producer.close(timeout=10)

    rule = event.get("rule", {})
    decoder = event.get("decoder", {})

    print("Archive replay publish: PASS")
    print("event_uid :", uid)

    print(
        "source    :",
        f"{relative}:{line_number}"
    )

    print(
        "rule      :",
        rule.get("id"),
        "level",
        rule.get("level"),
    )

    print(
        "decoder   :",
        decoder.get("name")
        if isinstance(decoder, dict)
        else None,
    )

    print(
        "location  :",
        event.get("location"),
    )

    for topic, partition, offset in payloads:
        print(
            "published :",
            topic,
            f"partition={partition}",
            f"offset={offset}",
        )


if __name__ == "__main__":
    main()
