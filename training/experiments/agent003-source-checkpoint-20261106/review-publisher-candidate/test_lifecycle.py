import copy,json,sqlite3,unittest,tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import catalog_lifecycle as core
import decision_review as review

def fixture():
    return {'schema_version':'nexus-human-review-v1','generated_at':'2026-11-05T04:00:00Z','automated_response_allowed':False,'items':[{
        'alert_id':'a'*64,'endpoint_id':'003','pipeline':'dfp','source_mode':'controlled-test','event_time':'2026-11-05T03:00:00Z',
        'detected_at':'2026-11-05T03:01:00Z','detector_id':'synthetic','detector_version':'test','feature_contract':'synthetic-counts',
        'coverage_status':'unknown','validation_status':'experimental','score':0,'score_semantics':'reconstruction-error',
        'findings':['Synthetic finding'],'limitations':['Synthetic only, not evaluated'],
        'evidence_refs':[{'event_uid':'b'*64,'sha256':'c'*64}],
        'recommendation':{'action':'investigate','reason':'Synthetic investigation'}}]}

def raw(obj):return json.dumps(obj).encode()

class Tests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        self.obj=fixture();self.old=raw(self.obj);self.pin=core.sha(self.old)
        self.new=copy.deepcopy(self.obj);self.new['items'][0]['recommendation']['reason']='Updated evidence recommendation'
        self.newraw=raw(self.new)
        self.db.executescript(review.SCHEMA)
        self.db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema_version','nexus-decision-store-v1'),('catalog_sha256',self.pin)])
        catalog=review.validate_catalog(self.obj)
        self.body={'request_id':'11111111-1111-4111-8111-111111111111','alert_id':'a'*64,
                   'alert_revision':catalog['items'][0]['alert_revision'],'expected_seq':0,'action':'investigating','reason':'Synthetic human review'}
        self.db.commit();self.db.execute('BEGIN IMMEDIATE')
        review.decision(self.db,self.body,{'actor_ref':'synthetic-reviewer'},catalog,'2026-11-05T04:00:00Z');self.db.commit()
        self.decisions=[tuple(r) for r in self.db.execute('SELECT * FROM decisions')]
    def advance(self):return core.advance(self.db,self.old,self.newraw,self.pin,'2026-11-05T04:01:00Z')
    def test_history_preserved_and_revision_changes(self):
        self.assertFalse(self.advance()['replayed'])
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM decisions')],self.decisions)
        review.check_store(self.db,core.sha(self.newraw))
        self.assertEqual(self.db.execute('SELECT count(*) FROM catalog_snapshots').fetchone()[0],2)
        self.assertNotEqual(review.validate_catalog(self.obj)['items'][0]['alert_revision'],review.validate_catalog(self.new)['items'][0]['alert_revision'])
    def test_retry_idempotent(self):
        self.advance();self.assertTrue(self.advance()['replayed'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM catalog_publications').fetchone()[0],1)
    def test_retired_alert_snapshot_preserved(self):
        self.new['items']=[];self.newraw=raw(self.new);self.advance()
        self.assertEqual(len(review.records(self.db,'a'*64)),1)
        self.assertEqual(bytes(self.db.execute('SELECT payload FROM catalog_snapshots WHERE sha256=?',(self.pin,)).fetchone()[0]),self.old)
    def test_stale_publication_rejected(self):
        self.advance();other=copy.deepcopy(self.obj);other['items'][0]['findings']=['Conflicting update']
        with self.assertRaises(ValueError):core.advance(self.db,self.old,raw(other),self.pin,'2026-11-05T04:02:00Z')
        review.check_store(self.db,core.sha(self.newraw))
    def test_raw_fields_foreign_scope_and_promotions_rejected(self):
        for change in ({'full_log':'private'},{'endpoint_id':'004'},{'validation_status':'validated'},{'coverage_status':'verified'}):
            obj=copy.deepcopy(self.new);obj['items'][0].update(change)
            with self.assertRaises((ValueError,review.Rejected)):core.advance(self.db,self.old,raw(obj),self.pin,'2026-11-05T04:02:00Z')
            review.check_store(self.db,self.pin)
    def test_rollback_after_insert_failure(self):
        for ddl in core.DDL:self.db.execute(ddl)
        self.db.execute("CREATE TRIGGER injected_failure BEFORE UPDATE ON metadata BEGIN SELECT RAISE(ABORT,'synthetic crash'); END")
        self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):self.advance()
        review.check_store(self.db,self.pin)
        self.assertEqual(self.db.execute('SELECT count(*) FROM catalog_snapshots').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM catalog_publications').fetchone()[0],0)
    def test_snapshots_and_publication_append_only(self):
        self.advance()
        for sql in ('DELETE FROM catalog_snapshots','UPDATE catalog_snapshots SET payload=x\'00\'','DELETE FROM catalog_publications'):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
            self.db.rollback()
    def test_legacy_worker_old_pin_fails_closed(self):
        self.advance()
        with self.assertRaises(review.Rejected):review.check_store(self.db,self.pin)
    def test_native_loss_and_zero_preserved(self):
        self.new['items'][0]['score']=175.5;self.newraw=raw(self.new);self.advance()
        self.assertEqual(review.validate_catalog(self.new)['items'][0]['score'],175.5)
    def test_unproven_retry_rejected(self):
        self.db.execute("UPDATE metadata SET value=? WHERE key='catalog_sha256'",(core.sha(self.newraw),));self.db.commit()
        with self.assertRaises(ValueError):self.advance()
    def test_concurrent_publishers_one_generation_wins(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            path=Path(tmp)/'synthetic.sqlite3'
            dest=sqlite3.connect(path);self.db.backup(dest);dest.close()
            changed=copy.deepcopy(self.new);changed['items'][0]['findings']=['Other competing update']
            def submit(newbytes):
                db=sqlite3.connect(path,timeout=3)
                try:
                    core.advance(db,self.old,newbytes,self.pin,'2026-11-05T04:02:00Z');return 'accepted'
                except ValueError:return 'stale'
                finally:db.close()
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(submit,[self.newraw,raw(changed)])),['accepted','stale'])
            db=sqlite3.connect(path)
            try:
                self.assertEqual(db.execute('SELECT count(*) FROM catalog_publications').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT count(*) FROM decisions').fetchone()[0],1)
            finally:db.close()
    def test_external_transaction_not_committed(self):
        self.db.execute('BEGIN')
        with self.assertRaises(ValueError):self.advance()
        self.assertTrue(self.db.in_transaction);self.db.rollback()
if __name__=='__main__':unittest.main(verbosity=2)
