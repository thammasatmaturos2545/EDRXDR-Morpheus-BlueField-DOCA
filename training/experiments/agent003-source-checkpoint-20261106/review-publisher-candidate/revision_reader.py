"""Offline candidate reader; anchor-pinned publication chain and immutable evidence."""
import hashlib, json
import decision_review as review

MAX_TRANSITIONS = 32
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024

def checked(raw, expected):
    review.need(type(raw) is bytes and len(raw) <= review.MAX_CATALOG
                and hashlib.sha256(raw).hexdigest() == expected,
                'CATALOG_HASH_MISMATCH', 503)
    try:
        return review.validate_catalog(review.parse_json(raw, 503))
    except review.Rejected:
        raise review.Rejected(503, 'INVALID_CATALOG')

def view(connection, anchor_raw, anchor_sha):
    anchor = checked(anchor_raw, anchor_sha)
    metadata = dict(connection.execute('SELECT key,value FROM metadata'))
    review.need(set(metadata) == {'schema_version', 'catalog_sha256'}
                and metadata['schema_version'] == 'nexus-decision-store-v1',
                'STORE_SCHEMA_MISMATCH', 503)
    active_sha = metadata['catalog_sha256']
    review.need(type(active_sha) is str and review.HASH.fullmatch(active_sha),
                'STORE_CATALOG_MISMATCH', 503)
    tables = {r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    lifecycle = {'catalog_snapshots', 'catalog_publications'}
    if not lifecycle & tables:
        review.need(active_sha == anchor_sha, 'STORE_CATALOG_MISMATCH', 503)
        return anchor, [anchor], active_sha
    review.need(lifecycle <= tables, 'INCOMPLETE_LIFECYCLE_SCHEMA', 503)
    publications = list(connection.execute(
        'SELECT previous_sha256,next_sha256,published_at FROM catalog_publications '
        'ORDER BY seq LIMIT ?', (MAX_TRANSITIONS + 1,)))
    review.need(len(publications) <= MAX_TRANSITIONS, 'CATALOG_HISTORY_LIMIT', 503)
    chain = [anchor_sha]
    for previous, following, published_at in publications:
        review.need(previous == chain[-1] and type(following) is str
                    and review.HASH.fullmatch(following) and following not in chain,
                    'INVALID_PUBLICATION_CHAIN', 503)
        try:
            review.timestamp(published_at)
        except review.Rejected:
            raise review.Rejected(503, 'INVALID_PUBLICATION_TIME')
        chain.append(following)
    review.need(chain[-1] == active_sha, 'STORE_CATALOG_MISMATCH', 503)
    catalogs, total = [], 0
    for digest in chain:
        row = connection.execute(
            'SELECT length(payload) FROM catalog_snapshots WHERE sha256=?', (digest,)).fetchone()
        review.need(row is not None and type(row[0]) is int
                    and row[0] <= review.MAX_CATALOG, 'CATALOG_SNAPSHOT_LIMIT', 503)
        total += row[0]
        review.need(total <= MAX_SNAPSHOT_BYTES, 'CATALOG_HISTORY_LIMIT', 503)
        raw = connection.execute(
            'SELECT payload FROM catalog_snapshots WHERE sha256=?', (digest,)).fetchone()[0]
        review.need(type(raw) is bytes, 'INVALID_CATALOG_STORAGE', 503)
        if digest == anchor_sha:
            review.need(raw == anchor_raw, 'CATALOG_ANCHOR_MISMATCH', 503)
        catalogs.append(checked(raw, digest))
    return catalogs[-1], catalogs, active_sha

def display_items(connection, active, catalogs):
    evidence, latest = {}, {}
    for catalog in catalogs:
        for row in catalog['items']:
            identity = row['alert_id']
            latest[identity] = row
            evidence.setdefault(identity, {})[row['alert_revision']] = row
    review.need(len(latest) <= review.MAX_ALERTS, 'ARCHIVED_ALERT_LIMIT', 503)
    active_ids = {row['alert_id'] for row in active['items']}
    items = []
    for identity, row in latest.items():
        history = review.records(connection, identity)
        revisions = evidence[identity]
        for record in history:
            review.need(record['alert_revision'] in revisions,
                        'AUDIT_EVIDENCE_UNAVAILABLE', 503)
        items.append(dict(row, retired=identity not in active_ids, history=history,
                          revision_evidence=revisions,
                          latest_seq=history[-1]['seq'] if history else 0))
    # Do not silently hide decisions for a missing/foreign alert.
    for (identity,) in connection.execute('SELECT DISTINCT alert_id FROM decisions'):
        review.need(identity in latest, 'AUDIT_ALERT_UNAVAILABLE', 503)
    return items

def decide(connection, body, actor, active, now):
    review.need(review.exact(body, (
        'request_id', 'alert_id', 'alert_revision', 'expected_seq', 'action', 'reason')))
    if type(body['request_id']) is str:
        previous = connection.execute(
            'SELECT * FROM decisions WHERE request_id=?', (body['request_id'],)).fetchone()
        if previous:
            request_hash = review.digest(dict(body, actor_ref=actor['actor_ref']))
            review.need(previous['request_hash'] == request_hash, 'IDEMPOTENCY_CONFLICT', 409)
            return {'replayed': True, 'decision': {
                key: previous[key] for key in previous.keys() if key != 'request_hash'}}
    return review.decision(connection, body, actor, active, now)

def handle(request, root, anchor_sha):
    review.need(review.exact(request, ('method', 'authorization', 'body')))
    review.need(request['method'] in ('GET', 'POST'))
    review.need(type(anchor_sha) is str and review.HASH.fullmatch(anchor_sha),
                'CATALOG_NOT_PINNED', 503)
    write = request['method'] == 'POST'
    registry = review.parse_json(review.secure_read(root, 'reviewers.json', 32768), 503)
    actor = review.principal(request['authorization'], registry, write)
    raw = review.secure_read(root, 'catalog-' + anchor_sha + '.json', review.MAX_CATALOG)
    checked(raw, anchor_sha)
    connection = review.connect(root, write)
    try:
        connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        active, catalogs, active_sha = view(connection, raw, anchor_sha)
        # Verify all historical evidence before returning facts or accepting decisions.
        items = display_items(connection, active, catalogs)
        if write:
            from datetime import datetime, timezone
            result = decide(connection, request['body'], actor, active,
                            datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
            connection.commit()
            return {'status': 200, 'body': dict(result, response_executed=False)}
        review.need(request['body'] is None)
        body = dict(active, items=items, principal=actor, catalog_sha256=active_sha,
                    anchor_catalog_sha256=anchor_sha, retired_items_read_only=True)
        review.need(len(review.canonical(body).encode()) <= MAX_RESPONSE_BYTES,
                    'REVIEW_RESPONSE_LIMIT', 503)
        return {'status': 200, 'body': body}
    finally:
        connection.close()
