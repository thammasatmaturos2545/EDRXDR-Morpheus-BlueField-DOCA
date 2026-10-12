"""Offline fixture-only journal binding. No sender, CLI or approval issuer.

Real quarantine provenance is deliberately unsupported until a trusted sink reader
is integrated. Input bytes are supplied by trusted caller code, not authenticated
by this offline API. Never expose this API directly to untrusted JSON requests.
"""
from copy import deepcopy
import bluefield_operator_contract as c
import bluefield_operator_store as s
from bluefield_operator_review import ReviewBook, actor_check


class BoundReviewBook(ReviewBook):
    def reserve_fixture(self, attempt_id, plan_hash, actor, actual_source, raw, low, high,
                        *, evidence_kind):
        actor_check(actor)
        c.token(attempt_id, c.IDENTITY, 'invalid_attempt_id')
        c.require(evidence_kind == 'synthetic_fixture', 'quarantine_provenance_not_integrated')
        actor, actual_source = deepcopy((actor, actual_source))
        # Review lookup, current approval, exact source and intent use ONE lock.
        # No caller-supplied approval/plan can override the canonical review.
        with self._transaction() as db:
            data = self._review(db, plan_hash)
            c.require(data['state'] == 'approved', 'canonical_approval_required')
            c.require(data['decision_actor'] == actor, 'approval_owner_required')
            plan, envelope, approval = data['plan'], data['envelope'], data['approval']
            c.require(envelope['run_id'].startswith('opread-') and
                      len(envelope['run_id']) == 39 and
                      all(x in '0123456789abcdef' for x in envelope['run_id'][7:]),
                      'not_fixture_namespace')
            now = c.now_checked(self.clock())
            authorization = c.authorize(plan, envelope, data['evidence_id'], approval, now, actor['name'])
            c.verify_source(plan, actual_source, raw, low, high)
            key = s._replay_key(plan)
            c.require(db.execute('SELECT 1 FROM attempts WHERE attempt_id=? OR approval_id=? OR replay_key=?',
                                 (attempt_id, approval['approval_id'], key)).fetchone() is None,
                      'attempt_approval_or_replay_already_reserved')
            events = []
            for state, reason in (('reviewed','review_created'),('approved','operator_approved'),
                                  ('intent_recorded','verified_original_bytes')):
                events.append(c.audit_event(events[-1] if events else None, attempt_id, plan_hash, state, reason, now))
            payload = {'plan':plan,'envelope':envelope,'evidence_id':data['evidence_id'],
                       'approval':approval,'trusted_operator':actor['name'],
                       'authorization_sha256':authorization,'events':events,'receipt':None}
            db.execute('INSERT INTO attempts VALUES (?,?,?,?,?)',
                       (attempt_id,approval['approval_id'],key,c.canonical(payload).decode(),c.digest(payload)))
            binding = {'attempt_id':attempt_id,'plan_sha256':plan_hash,'actor':actor,
                       'evidence_kind':'synthetic_fixture','input_sha256':plan['input_sha256'],
                       'source':actual_source,'low':low,'high':high,'byte_count':len(raw)}
            # New table created only with a valid reservation in the SAME transaction.
            db.execute('CREATE TABLE IF NOT EXISTS fixture_bindings (attempt_id TEXT PRIMARY KEY, payload TEXT NOT NULL, seal TEXT NOT NULL)')
            db.execute('INSERT INTO fixture_bindings VALUES (?,?,?)',
                       (attempt_id,c.canonical(binding).decode(),c.digest(binding)))
        return {'attempt_id':attempt_id,'state':'intent_recorded','evidence_kind':'synthetic_fixture',
                'transport_enabled':False,'replay_authorized':False}

    def inspect_binding(self, attempt_id):
        with self._transaction() as db:
            payload = self._load(db, attempt_id)
            row = db.execute('SELECT payload,seal FROM fixture_bindings WHERE attempt_id=?',(attempt_id,)).fetchone()
            c.require(row is not None,'binding_missing')
            import json
            value = json.loads(row[0])
            c.exact(value,{'attempt_id','plan_sha256','actor','evidence_kind','input_sha256','source','low','high','byte_count'},'binding_invalid')
            c.require(c.digest(value)==row[1] and value['attempt_id']==attempt_id and
                      value['plan_sha256']==payload['plan']['plan_sha256'] and
                      value['source']==payload['plan']['source'] and
                      value['input_sha256']==payload['plan']['input_sha256'] and
                      value['evidence_kind']=='synthetic_fixture','binding_changed')
            review = self._review(db,value['plan_sha256'])
            c.require(review['state']=='approved' and review['approval']==payload['approval'] and
                      review['decision_actor']==value['actor'],'canonical_binding_changed')
            return {'binding':value,'state':payload['events'][-1]['state'],
                    'transport_enabled':False,'replay_authorized':False}
