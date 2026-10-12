"""Offline canonical-journal binding tests; synthetic approvals only."""
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import bluefield_operator_contract as c
import bluefield_operator_review as r
import bluefield_operator_binding as b
import bluefield_operator_fixture as f


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'journal.db'
        _,self.env,self.eid=f.bundle('opread-'+'a'*32)
        self.now=datetime.now(timezone.utc)
        self.actor={'uid':1001,'name':'fixture-user'}
        r.initialize(self.path,self.actor,clock=lambda:self.now)
        self.book=b.BoundReviewBook(self.path,clock=lambda:self.now)
        self.plan=self.book.review(self.env,self.eid,'shadow-bluefield-controlled-replay-fixture01',self.actor)
    def approve(self):
        self.book.decide(self.plan['plan_sha256'],self.actor,True,confirmed=True)
    def reserve(self, **kw):
        args=dict(attempt_id='attempt01',plan_hash=self.plan['plan_sha256'],actor=self.actor,
                  actual_source=self.plan['source'],raw=f.RAW,low=0,high=1,evidence_kind='synthetic_fixture')
        args.update(kw)
        return self.book.reserve_fixture(**args)
    def test_pending_cannot_reserve(self):
        with self.assertRaisesRegex(c.Rejected,'canonical_approval_required'): self.reserve()
    def test_approved_binding_survives_reopen(self):
        self.approve(); result=self.reserve()
        self.assertFalse(result['transport_enabled'])
        fresh=b.BoundReviewBook(self.path,clock=lambda:self.now)
        out=fresh.inspect_binding('attempt01')
        self.assertEqual(out['binding']['actor'],self.actor)
        self.assertNotIn('carrier',str(out))
        self.assertEqual(fresh.inspect('attempt01')['state'],'intent_recorded')
    def test_wrong_uid_same_name_denied(self):
        self.approve()
        with self.assertRaisesRegex(c.Rejected,'approval_owner_required'):
            self.reserve(actor={'uid':1002,'name':'fixture-user'})
    def test_expired_approval_denied(self):
        self.approve(); self.now+=timedelta(hours=1)
        with self.assertRaises(c.Rejected): self.reserve()
    def test_hash_mismatch_no_intent(self):
        self.approve()
        with self.assertRaisesRegex(c.Rejected,'source_hash_mismatch'): self.reserve(raw=b'changed')
        with self.assertRaisesRegex(c.Rejected,'attempt_not_found'): self.book.inspect('attempt01')
    def test_retention_loss(self):
        self.approve()
        with self.assertRaisesRegex(c.Rejected,'source_unavailable'): self.reserve(low=1,high=1)
    def test_quarantine_label_rejected(self):
        self.approve()
        with self.assertRaisesRegex(c.Rejected,'quarantine_provenance_not_integrated'):
            self.reserve(evidence_kind='verified_quarantine')
    def test_duplicate_blocked(self):
        self.approve(); self.reserve()
        with self.assertRaises(c.Rejected): self.reserve(attempt_id='attempt02')
    def test_rejected_review_denied(self):
        self.book.decide(self.plan['plan_sha256'],self.actor,False)
        with self.assertRaisesRegex(c.Rejected,'canonical_approval_required'): self.reserve()
    def test_commit_failure_rolls_back_binding_and_intent(self):
        self.approve()
        with patch.object(self.book,'_commit',side_effect=RuntimeError('disk')):
            with self.assertRaises(RuntimeError): self.reserve()
        with self.assertRaisesRegex(c.Rejected,'attempt_not_found'): self.book.inspect('attempt01')
        self.reserve()
    def test_no_external_approval_parameter(self):
        self.approve()
        with self.assertRaises(TypeError): self.reserve(approval={})
    def test_different_journal_cannot_supply_approval(self):
        self.approve()
        other=Path(self.tmp.name)/'other.db'; r.initialize(other,self.actor,clock=lambda:self.now)
        self.book=b.BoundReviewBook(other,clock=lambda:self.now)
        with self.assertRaisesRegex(c.Rejected,'review_not_found'): self.reserve()


if __name__ == '__main__': unittest.main(verbosity=2)
