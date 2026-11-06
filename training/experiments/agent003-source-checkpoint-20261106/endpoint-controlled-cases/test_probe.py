import sys, types, unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch as mock
if sys.platform=='win32': sys.modules['fcntl']=types.SimpleNamespace()
import probe
class Tests(unittest.TestCase):
    def test_agent_type_formats(self):
        for value in ('agent', 'agent\n', 'WAZUH_TYPE="agent"', "WAZUH_TYPE='agent'", 'WAZUH_TYPE=agent'):
            self.assertTrue(probe.verified_agent_type(value))
        for value in ('manager', 'server', '', 'not agent', 'agent\nserver', 'WAZUH_TYPE="server"'):
            self.assertFalse(probe.verified_agent_type(value))
    def test_only_test_directory_added(self):
        original=b'<ossec_config><syscheck><disabled>no</disabled><frequency>43200</frequency></syscheck></ossec_config>'
        out=probe.patch(original,'/var/lib/edrxdr-endpoint-probes/probe-abc_123/files')
        self.assertEqual(out.replace(b'\n    <directories realtime="yes" check_all="yes" report_changes="no">/var/lib/edrxdr-endpoint-probes/probe-abc_123/files</directories>\n',b''),original)
        self.assertNotIn(b'whodata',out)
    def test_disabled_rejected(self):
        with self.assertRaises(ValueError): probe.patch(b'<syscheck><disabled>yes</disabled></syscheck>','/var/lib/edrxdr-endpoint-probes/probe-abc/files')
    def test_foreign_directory_rejected(self):
        with self.assertRaises(ValueError): probe.patch(b'<syscheck><disabled>no</disabled></syscheck>','/home/user')
    def test_duplicate_blocks_rejected(self):
        with self.assertRaises(ValueError): probe.patch(b'<syscheck/><syscheck/>','/var/lib/edrxdr-endpoint-probes/probe-abc/files')
    def test_entities_rejected(self):
        with self.assertRaises(ValueError): probe.patch(b'<!DOCTYPE a><syscheck/>','/var/lib/edrxdr-endpoint-probes/probe-abc/files')
    def test_restore_concurrent_edit_preserved(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            root=Path(tmp); cfg=root/'config';original=b'<syscheck><disabled>no</disabled></syscheck>'
            proposed=probe.patch(original,'/var/lib/edrxdr-endpoint-probes/probe-abc/files')
            entry=proposed.replace(original.split(b'</syscheck>')[0],b'',1).replace(b'</syscheck>',b'').decode()
            cfg.write_bytes(proposed+b'<!-- administrator edit -->')
            (root/'original.conf').write_bytes(original)
            (root/'receipt.json').write_text(json.dumps({'original_sha256':probe.digest(original),'proposed_sha256':probe.digest(proposed),'entry':entry}))
            fake=types.SimpleNamespace(flock=lambda *a:None,LOCK_EX=1)
            with mock.object(probe,'CONFIG',cfg),mock.object(probe,'fcntl',fake),mock.object(probe,'command'),mock.object(probe,'write_config',side_effect=lambda b,m:cfg.write_bytes(b)):
                probe.restore(root)
            self.assertEqual(cfg.read_bytes(),original+b'<!-- administrator edit -->')
    def test_restore_conflict_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            root=Path(tmp); cfg=root/'config';cfg.write_bytes(b'concurrent unrelated content')
            (root/'original.conf').write_bytes(b'original')
            (root/'receipt.json').write_text(json.dumps({'original_sha256':probe.digest(b'original'),'proposed_sha256':'different','entry':'absent'}))
            fake=types.SimpleNamespace(flock=lambda *a:None,LOCK_EX=1)
            with mock.object(probe,'CONFIG',cfg),mock.object(probe,'fcntl',fake),mock.object(probe,'command'),mock.object(probe,'write_config') as write:
                with self.assertRaises(RuntimeError): probe.restore(root)
                write.assert_not_called()
if __name__=='__main__': unittest.main()
