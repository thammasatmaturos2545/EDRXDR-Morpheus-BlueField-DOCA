"""Read-only diagnostic probe for the Wazuh UID scanner.

Uses Filebeat's existing connection configuration inside the
Wazuh Manager container. Not intended as production API auth.
"""

import json
import subprocess

from uid_lookup.bounded_scan import scan_wazuh

MANAGER = "wazuh-wazuh.manager-1"

REMOTE = r'''
import ast
import base64
import json
import os
import re
import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen

payload = json.load(sys.stdin)

method = payload["method"]
path = payload["path"]

allowed = {
    ("POST", "/wazuh-alerts-4.x-*/_search?scroll=1m"),
    ("POST", "/_search/scroll"),
    ("DELETE", "/_search/scroll"),
}

is_planned_search = (
    method == "POST"
    and re.fullmatch(
        r"/wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}(?:,wazuh-alerts-4\.x-\d{4}\.\d{2}\.\d{2}){0,127}/_search\?scroll=1m",
        path,
    ) is not None
)

if (method, path) not in allowed and not is_planned_search:
    sys.exit(2)

config = Path("/etc/filebeat/filebeat.yml").read_text()
match = re.search(r"(?m)^output\.elasticsearch:\s*$", config)

if not match:
    sys.exit(3)

fields = {}

for line in config[match.end():].splitlines():
    if line.strip() and not line[0].isspace() and not line.lstrip().startswith("#"):
        break

    m = re.match(r"^\s+([\w.-]+):\s*(.*?)\s*$", line)
    if m:
        fields[m.group(1)] = m.group(2)

def value(name):
    raw = fields.get(name, "").strip()

    if raw.startswith("["):
        raw = ast.literal_eval(raw)[0]

    raw = str(raw).strip("'\"")
    m = re.fullmatch(r"\$\{([A-Za-z_]\w*)(?::([^}]*))?\}", raw)

    return os.environ.get(m.group(1), m.group(2) or "") if m else raw

host = value("hosts").rstrip("/")
user = value("username")
password = value("password")

if not host.startswith("https://") or not user or not password:
    sys.exit(4)

ctx = ssl.create_default_context(
    cafile=value("ssl.certificate_authorities") or None
)

cert = value("ssl.certificate")
key = value("ssl.key")

if cert and key:
    ctx.load_cert_chain(cert, key)

auth = base64.b64encode(
    f"{user}:{password}".encode()
).decode()

req = Request(
    host + path,
    data=json.dumps(payload["body"]).encode(),
    headers={
        "Authorization": "Basic " + auth,
        "Content-Type": "application/json",
    },
    method=method,
)

try:
    with urlopen(req, context=ctx, timeout=15) as response:
        print(response.read().decode())
except Exception as exc:
    from urllib.error import HTTPError, URLError

    if isinstance(exc, HTTPError):
        try:
            detail = json.loads(exc.read(4096))
            error = detail.get("error", {})
            causes = error.get("root_cause", [])
            cause = causes[0] if causes else error
            kind = cause.get("type", "unknown")
            kind = re.sub(r"[^a-zA-Z0-9_]", "", str(kind))[:25]
        except (ValueError, TypeError, AttributeError, KeyError, IndexError):
            kind = "unknown"

        
        reason = str(
            error.get("reason")
            or cause.get("reason")
            or "unknown"
        )

        reason = re.sub(
            r"(?i)^validation failed:\s*\d+:\s*",
            "",
            reason
        )

        hint = re.sub(
            r"[^a-z0-9]+",
            "_",
            reason.lower()
        ).strip("_")[:32]

        print(
            "DIAG_" + (hint or "unknown"),
            file=sys.stderr
        )

    elif isinstance(exc, ssl.SSLError):
        print("DIAG_TLS_ERROR", file=sys.stderr)
    elif isinstance(exc, URLError):
        print("DIAG_URL_ERROR", file=sys.stderr)
    else:
        print("DIAG_" + type(exc).__name__.upper(), file=sys.stderr)

    sys.exit(5)
'''


def request(method, path, body):
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            MANAGER,
            "python3",
            "-c",
            REMOTE,
        ],
        input=json.dumps({
            "method": method,
            "path": path,
            "body": body,
        }),
        capture_output=True,
        text=True,
        timeout=20,
    )

    if result.returncode != 0:
        diagnostic = result.stderr.strip()

        if (
            not diagnostic.startswith("DIAG_")
            or len(diagnostic) > 40
            or not diagnostic.replace("_", "").isalnum()
        ):
            diagnostic = "DIAG_UNAVAILABLE"

        raise RuntimeError(
            f"Indexer request failed: exit={result.returncode}, "
            f"{diagnostic}"
        )

    return json.loads(result.stdout)


if __name__ == "__main__":
    result = scan_wazuh(
        request,
        page_size=5,
        max_documents=10,
    )

    records = result["records"]

    print("=== REAL WAZUH UID SCAN ===")
    print("SCANNED=", result["scanned"])
    print("LOOKUP_RECORDS=", len(records))
    print("REJECTED=", result["rejected"])
    print("UNIQUE_UIDS=", len({
        record["_source"]["event_uid"]
        for record in records
    }))
    print("COMPLETE=", result["complete"])
    print("SOURCE_INDEX_MODIFIED=False")
