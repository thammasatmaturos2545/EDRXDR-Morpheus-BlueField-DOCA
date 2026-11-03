import copy
import unittest
from acceptance import evaluate


def gate(name, deps=None):
    return {'id':name, 'required':True, 'depends_on':deps or [], 'status':'pending'}


def receipt():
    return dict(reviewed=True, receipt_sha256='a'*64, source_manifest_sha256='b'*64)


class AcceptanceTests(unittest.TestCase):
    def test_pending_does_not_deliver(self):
        result=evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[gate('live')]})
        self.assertFalse(result['delivery_accepted'])

    def test_menu_or_sample_without_receipt_cannot_pass(self):
        item=gate('quality'); item['status']='passed'
        with self.assertRaises(ValueError): evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[item]})

    def test_independent_quality_required(self):
        item=gate('quality'); item.update(status='passed',acceptance_receipt=receipt(),independent_evaluation_required=True)
        with self.assertRaises(ValueError): evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[item]})

    def test_dependency_and_cycle(self):
        a,b=gate('data'),gate('model',['data']); b.update(status='passed',acceptance_receipt=receipt())
        with self.assertRaises(ValueError): evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[a,b]})
        b['status']='pending';a['depends_on']=['model']
        with self.assertRaises(ValueError): evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[a,b]})

    def test_unapproved_waiver_rejected(self):
        item=gate('network_scope');item['required']=False
        with self.assertRaises(ValueError): evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[item]})

    def test_complete_receipts_structurally_pass_but_not_authenticate(self):
        a,b=gate('data'),gate('model',['data'])
        for item in (a,b): item.update(status='passed',acceptance_receipt=receipt())
        result=evaluate({'schema':'edrxdr-delivery-acceptance-1','items':[a,b]})
        self.assertTrue(result['delivery_accepted']);self.assertFalse(result['receipt_authenticity_verified'])


if __name__=='__main__': unittest.main()
