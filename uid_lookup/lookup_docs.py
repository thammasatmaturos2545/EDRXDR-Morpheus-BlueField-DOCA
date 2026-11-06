"""Build bounded, minimal Wazuh UID lookup documents."""

import hashlib
import re
from collections.abc import Mapping

from uid_lookup.wazuh_uid import wazuh_event_uid

SCHEMA = "edrxdr-wazuh-uid-lookup-v1"

INDEX_PATTERN = re.compile(
    r"wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}"
)


def build_lookup_doc(hit):
    """Convert one OpenSearch hit into a minimal lookup record."""

    if not isinstance(hit, Mapping):
        raise ValueError("Invalid search hit")

    index = hit.get("_index")
    document_id = hit.get("_id")
    source = hit.get("_source")

    if (
        not isinstance(index, str)
        or not INDEX_PATTERN.fullmatch(index)
    ):
        raise ValueError("Invalid Wazuh source index")

    if (
        not isinstance(document_id, str)
        or not document_id
        or len(document_id) > 512
    ):
        raise ValueError("Invalid source document ID")

    uid = wazuh_event_uid(source)

    if uid is None:
        raise ValueError("Invalid Wazuh event identity")

    # Length-prefix each part to avoid ambiguous concatenation.
    reference = "|".join(
        f"{len(value.encode('utf-8'))}:{value}"
        for value in (index, document_id)
    )

    lookup_id = hashlib.sha256(
        reference.encode("utf-8")
    ).hexdigest()

    return {
        "_id": lookup_id,
        "_source": {
            "schema_version": SCHEMA,
            "event_uid": uid,
            "source_index": index,
            "source_document_id": document_id,
            "production_ready": False,
            "automated_response_allowed": False,
        },
    }
