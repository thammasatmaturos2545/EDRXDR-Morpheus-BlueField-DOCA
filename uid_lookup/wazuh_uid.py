"""Exact Wazuh event identity for UID lookup indexing."""

import hashlib
from collections.abc import Mapping


def identity_part(value):
    if isinstance(value, str):
        text = value.strip()
    elif type(value) is int and abs(value) <= 9007199254740991:
        text = str(value)
    else:
        # Reject unsupported values rather than risk a wrong UID.
        return None

    return text or None


def wazuh_event_uid(event):
    if not isinstance(event, Mapping):
        return None

    manager = event.get("manager")
    agent = event.get("agent")

    if not isinstance(manager, Mapping):
        return None
    if not isinstance(agent, Mapping):
        return None

    values = [
        manager.get("name"),
        agent.get("id"),
        event.get("id"),
    ]

    parts = [identity_part(value) for value in values]

    if any(part is None for part in parts):
        return None

    canonical = "wazuh-v1|" + "|".join(
        f"{len(part.encode('utf-8'))}:{part}"
        for part in parts
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
