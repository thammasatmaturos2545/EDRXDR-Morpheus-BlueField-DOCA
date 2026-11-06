import base64, copy, hashlib, json, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import decision_review as review
import catalog_lifecycle as publisher
import revision_reader as reader
from test_lifecycle import fixture, raw

PASSWORD = 'synthetic-password-not-a-real-secret'
def registry(role='reviewer'):
    salt = bytes(range(16))
    return {'schema_version': 'nexus-reviewers-v1', 'users': [{
        'login': 'synthetic', 'actor_ref': 'synthetic-actor', 'role': role,
        'salt': salt.hex(), 'scrypt_sha256': hashlib.scrypt(
            PASSWORD.encode(), salt=salt, n=16384, r=8, p=1, dklen=64).hex()}]}
AUTH = 'Basic ' + base64.b64encode(('synthetic:' + PASSWORD).encode()).decode()

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'decisions.sqlite3'
        self.old = fixture(); self.oldraw = raw(self.old); self.pin = publisher.sha(self.oldraw)
        self.new = copy.deepcopy(self.old)
        self.new['items'][0]['recommendation']['reason'] = 'Updated synthetic recommendation'
        self.newraw = raw(self.new)
        db = self.connect()
        db.executescript(review.SCHEMA)
        db.executemany('INSERT INTO metadata VALUES (?,?)', [
            ('schema_version', 'nexus-decision-store-v1'), ('catalog_sha256', self.pin)])
        db.commit(); db.close()
        self.body = {'request_id': '11111111-1111-4111-8111-111111111111',
            'alert_id': 'a'*64, 'alert_revision': review.validate_catalog(self.old)['items'][0]['alert_revision'],
            'expected_seq': 0, 'action': 'agree_recommendation', 'reason': 'Synthetic human reason'}
    def connect(self, *args):
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        return db
    def call(self, method='GET', body=None, auth=AUTH, role='reviewer'):
        users = raw(registry(role))
        def read(root, name, maximum):
            return users if name == 'reviewers.json' else self.oldraw
        with patch.object(review, 'secure_read', side_effect=read), \
                patch.object(review, 'connect', side_effect=self.connect):
            return reader.handle({'method': method, 'authorization': auth, 'body': body},
                                 Path('/synthetic-private-root'), self.pin)
    def publish(self):
        db = self.connect()
        try:
            publisher.advance(db, self.oldraw, self.newraw, self.pin, '2026-11-05T05:00:00Z')
        finally:
            db.close()
    def corrupt(self, sql):
        db = self.connect()
        try:
            db.executescript(sql); db.commit()
        finally:
            db.close()
    @unittest.skipUnless(hasattr(__import__('os'), 'getuid'), 'POSIX private storage requires VM')
    def test_actual_private_reader_after_publication(self):
        self.call('POST', self.body); self.publish()
        root=Path(self.temp.name).resolve(); root.chmod(0o700); self.path.chmod(0o600)
        for name, contents in [('reviewers.json',raw(registry())),('catalog-'+self.pin+'.json',self.oldraw)]:
            target=root/name;target.write_bytes(contents);target.chmod(0o600)
        result=reader.handle({'method':'GET','authorization':AUTH,'body':None},root,self.pin)
        self.assertEqual(result['status'],200)
        self.assertEqual(len(result['body']['items'][0]['history']),1)
        import subprocess,sys
        request={'method':'GET','authorization':AUTH,'body':None}
        output=subprocess.run([sys.executable,'-B',str(Path(__file__).parent/'frontend/server/revision_worker.py'),
            '--root',str(root),'--catalog-sha256',self.pin],input=json.dumps(request).encode(),
            capture_output=True,check=True,timeout=8)
        decoded=json.loads(output.stdout)
        self.assertEqual(decoded['status'],200)
        self.assertEqual(decoded['body']['catalog_sha256'],publisher.sha(self.newraw))

    def test_staged_registry_uses_existing_named_auth_contract(self):
        from prepare_reviewers import entry
        user=entry('synthetic','reviewer',PASSWORD,bytes(range(16)))
        users={'schema_version':'nexus-reviewers-v1','users':[user]}
        self.assertEqual(review.principal(AUTH,users,True)['actor_ref'],'reviewer:synthetic')
        self.assertNotIn(PASSWORD,json.dumps(users))
    def test_legacy_single_batch_compatible(self):
        result = self.call()['body']
        self.assertEqual(result['catalog_sha256'], self.pin)
        self.assertFalse(result['items'][0]['retired'])
    def test_update_shows_original_reviewed_evidence(self):
        self.call('POST', self.body); self.publish()
        body = self.call()['body']; item = body['items'][0]
        self.assertNotEqual(item['alert_revision'], self.body['alert_revision'])
        self.assertEqual(item['history'][0]['alert_revision'], self.body['alert_revision'])
        prior = item['revision_evidence'][self.body['alert_revision']]
        self.assertEqual(prior['recommendation'], self.old['items'][0]['recommendation'])
        self.assertEqual(body['catalog_sha256'], publisher.sha(self.newraw))
        self.assertFalse(body['response_execution_enabled'])
    def test_retry_after_revision_update_returns_original(self):
        first = self.call('POST', self.body); self.publish()
        retry = self.call('POST', self.body)
        self.assertTrue(retry['body']['replayed'])
        self.assertEqual(first['body']['decision'], retry['body']['decision'])
    def test_stale_new_request_rejected(self):
        self.publish(); body = dict(self.body, request_id='22222222-2222-4222-8222-222222222222')
        with self.assertRaises(review.Rejected) as exc: self.call('POST', body)
        self.assertEqual(exc.exception.code, 'ALERT_REVISION_CHANGED')
    def test_retired_items_read_only_history_visible(self):
        self.call('POST', self.body); self.new['items']=[];self.newraw=raw(self.new);self.publish()
        item = self.call()['body']['items'][0]
        self.assertTrue(item['retired']); self.assertEqual(len(item['history']),1)
        body = dict(self.body,request_id='22222222-2222-4222-8222-222222222222',expected_seq=1)
        with self.assertRaises(review.Rejected) as exc:self.call('POST',body)
        self.assertEqual(exc.exception.status,404)
    def test_auth_denial_before_catalog_or_database(self):
        reads = []
        def read(root,name,maximum):
            reads.append(name);return raw(registry())
        with patch.object(review,'secure_read',side_effect=read),patch.object(review,'connect') as connect:
            with self.assertRaises(review.Rejected):
                reader.handle({'method':'GET','authorization':'','body':None},Path('/synthetic'),self.pin)
            connect.assert_not_called()
        self.assertEqual(reads,['reviewers.json'])
    def test_viewer_cannot_write(self):
        with self.assertRaises(review.Rejected) as exc:self.call('POST',self.body,role='viewer')
        self.assertEqual(exc.exception.status,403)
    def test_tampered_snapshot_rejected(self):
        self.publish()
        self.corrupt("DROP TRIGGER no_catalog_update; UPDATE catalog_snapshots SET payload=x'00';")
        with self.assertRaises(review.Rejected):self.call()
    def test_broken_publication_chain_rejected(self):
        self.publish()
        self.corrupt("DROP TRIGGER no_publication_update; UPDATE catalog_publications SET previous_sha256='"+'f'*64+"';")
        with self.assertRaises(review.Rejected):self.call()
    def test_missing_anchor_snapshot_rejected(self):
        self.publish()
        self.corrupt("DROP TRIGGER no_catalog_delete; DELETE FROM catalog_snapshots WHERE sha256='"+self.pin+"';")
        with self.assertRaises(review.Rejected):self.call()
    def test_missing_decision_revision_rejected(self):
        self.call('POST',self.body);self.publish()
        self.corrupt("DROP TRIGGER no_decision_update; UPDATE decisions SET alert_revision='"+'f'*64+"';")
        with self.assertRaises(review.Rejected):self.call()
    def test_historical_catalog_reactivation_rejected(self):
        self.publish(); db=self.connect()
        try:
            with self.assertRaises(ValueError):
                publisher.advance(db,self.newraw,self.oldraw,publisher.sha(self.newraw),'2026-11-05T06:00:00Z')
        finally:db.close()
    def test_cumulative_alert_limit_before_publish(self):
        self.new['items']=[]
        for n in range(20):
            item=copy.deepcopy(self.old['items'][0]);item['alert_id']=f'{n+1:064x}'
            self.new['items'].append(item)
        self.newraw=raw(self.new)
        with self.assertRaises(ValueError):self.publish()
        self.assertEqual(self.call()['body']['catalog_sha256'],self.pin)
    def test_duplicate_request_changed_actor_or_reason_conflicts(self):
        self.call('POST',self.body);self.publish()
        with self.assertRaises(review.Rejected) as exc:
            self.call('POST',dict(self.body,reason='Changed synthetic reason'))
        self.assertEqual(exc.exception.status,409)

if __name__ == '__main__':
    unittest.main(verbosity=2)
