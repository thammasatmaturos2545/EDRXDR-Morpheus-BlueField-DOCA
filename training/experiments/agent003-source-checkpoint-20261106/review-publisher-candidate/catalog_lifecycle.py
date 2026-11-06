"""Offline SQLite catalog lifecycle core. Not a trusted evidence publisher or live adapter."""
import hashlib
import decision_review as review

DDL=(
 'CREATE TABLE IF NOT EXISTS catalog_snapshots (sha256 TEXT PRIMARY KEY, payload BLOB NOT NULL)',
 'CREATE TABLE IF NOT EXISTS catalog_publications (seq INTEGER PRIMARY KEY AUTOINCREMENT, previous_sha256 TEXT NOT NULL, next_sha256 TEXT NOT NULL, published_at TEXT NOT NULL, UNIQUE(previous_sha256,next_sha256))',
 "CREATE TRIGGER IF NOT EXISTS no_catalog_update BEFORE UPDATE ON catalog_snapshots BEGIN SELECT RAISE(ABORT,'immutable catalog'); END",
 "CREATE TRIGGER IF NOT EXISTS no_catalog_delete BEFORE DELETE ON catalog_snapshots BEGIN SELECT RAISE(ABORT,'immutable catalog'); END",
 "CREATE TRIGGER IF NOT EXISTS no_publication_update BEFORE UPDATE ON catalog_publications BEGIN SELECT RAISE(ABORT,'append only'); END",
 "CREATE TRIGGER IF NOT EXISTS no_publication_delete BEFORE DELETE ON catalog_publications BEGIN SELECT RAISE(ABORT,'append only'); END",
)

def sha(raw): return hashlib.sha256(raw).hexdigest()

def checked(raw):
    if type(raw) is not bytes or len(raw)>review.MAX_CATALOG:raise ValueError('Catalog byte limit/type')
    return review.validate_catalog(review.parse_json(raw,503))

def advance(connection, old_raw, new_raw, expected_previous, now):
    """Caller owns a disposable offline DB; all changes transactional. No file/network IO."""
    if connection.in_transaction:raise ValueError('Caller transaction must be closed')
    review.timestamp(now)
    old=checked(old_raw);new=checked(new_raw)
    if sha(old_raw)!=expected_previous:raise ValueError('Expected source pin mismatch')
    # No quality promotion or containment recommendation accepted by this development core.
    for item in new['items']:
        if item['validation_status']!='experimental' or item['coverage_status']=='verified' or item['recommendation']['action']!='investigate':
            raise ValueError('Evidence approval/promotion not supported')
    next_hash=sha(new_raw)
    connection.execute('BEGIN IMMEDIATE')
    try:
        for sql in DDL:connection.execute(sql)
        metadata=dict(connection.execute('SELECT key,value FROM metadata'))
        if metadata.get('schema_version')!='nexus-decision-store-v1' or set(metadata)!={'schema_version','catalog_sha256'}:
            raise ValueError('Unsupported store metadata')
        current=metadata['catalog_sha256']
        if current==next_hash and next_hash!=expected_previous:
            retry=connection.execute('SELECT 1 FROM catalog_publications WHERE previous_sha256=? AND next_sha256=?',
                (expected_previous,next_hash)).fetchone()
            if not retry:raise ValueError('Unproven publication retry')
            for raw in (old_raw,new_raw):
                row=connection.execute('SELECT payload FROM catalog_snapshots WHERE sha256=?',(sha(raw),)).fetchone()
                if row is None or bytes(row[0])!=raw:raise ValueError('Snapshot mismatch')
            connection.commit();return {'replayed':True,'catalog_sha256':next_hash}
        if current!=expected_previous:raise ValueError('Stale catalog generation')
        if next_hash != current:
            if connection.execute('SELECT 1 FROM catalog_snapshots WHERE sha256=?',(next_hash,)).fetchone():
                raise ValueError('Historical catalog reactivation not supported')
            if connection.execute('SELECT count(*) FROM catalog_publications').fetchone()[0] >= 32:
                raise ValueError('Publication history limit')
            total=connection.execute('SELECT COALESCE(SUM(length(payload)),0) FROM catalog_snapshots').fetchone()[0]
            if total+len(new_raw)+(0 if connection.execute('SELECT 1 FROM catalog_snapshots WHERE sha256=?',(expected_previous,)).fetchone() else len(old_raw)) > 2*1024*1024:
                raise ValueError('Snapshot history byte limit')
            identities={row['alert_id'] for row in new['items']}|{row['alert_id'] for row in old['items']}
            for (stored,) in connection.execute('SELECT payload FROM catalog_snapshots'):
                identities.update(row['alert_id'] for row in checked(bytes(stored))['items'])
            if len(identities)>review.MAX_ALERTS:
                raise ValueError('Cumulative alert history limit')
        for raw in (old_raw,new_raw):
            digest=sha(raw)
            row=connection.execute('SELECT payload FROM catalog_snapshots WHERE sha256=?',(digest,)).fetchone()
            if row is not None and bytes(row[0])!=raw:raise ValueError('Snapshot conflict')
            connection.execute('INSERT OR IGNORE INTO catalog_snapshots VALUES (?,?)',(digest,raw))
        if next_hash==current:
            connection.commit();return {'replayed':True,'catalog_sha256':current}
        connection.execute('INSERT INTO catalog_publications(previous_sha256,next_sha256,published_at) VALUES (?,?,?)',
            (current,next_hash,now))
        changed=connection.execute("UPDATE metadata SET value=? WHERE key='catalog_sha256' AND value=?",(next_hash,current))
        if changed.rowcount!=1:raise ValueError('Concurrent catalog change')
        connection.commit()
        return {'replayed':False,'catalog_sha256':next_hash}
    except Exception:
        connection.rollback();raise
