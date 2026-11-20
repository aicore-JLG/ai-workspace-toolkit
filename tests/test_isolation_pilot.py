"""Offline evidence-contract tests. These do not run Docker or prove isolation."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import isolation_pilot as pilot


class IsolationPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'synthetic pilot'
        self.image = 'sha256:' + '1'*64

    def fixture(self):
        pilot.prepare(self.root, self.image)
        data = json.loads((self.root/'pilot.json').read_text())
        result = {'schema':1,'nonce':data['nonce'],'checks':{key:True for key in pilot.CHECKS}}
        container = {'Name':'/'+data['name'],'Image':self.image,
            'Config': {'Image':self.image,'User':'65534:65534','Entrypoint':['python3'],
                       'Cmd':['/input/probe.py'],'WorkingDir':'/tmp','Env':['PATH=/usr/bin']},
            'State': {'Running':False,'ExitCode':0,'OOMKilled':False,'Error':''},
            'HostConfig': {'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,
                'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges:true'],'PidsLimit':32,
                'Memory':134217728,'NanoCpus':1000000000,
                'Tmpfs':{'/tmp':'rw,noexec,nosuid,nodev,size=16m'}},
            'Mounts':[{'Destination':'/input','Source':str(self.root/'client-a'),'RW':False,'Type':'bind'},
                      {'Destination':'/output','Source':str(self.root/'output'),'RW':True,'Type':'bind'}]}
        self.save_report(result, container)
        return result, container

    def save_report(self, result, container):
        (self.root/'output/result.json').write_text(json.dumps(result))
        (self.root/'output/write-canary.txt').write_bytes(b'synthetic scoped output\n')
        (self.root/'container-inspect.json').write_text(json.dumps([container]))

    def refused(self):
        out=io.StringIO()
        with redirect_stdout(out):
            code=pilot.main(['--directory',str(self.root),'--validate'])
        self.assertEqual(code,1)
        self.assertEqual(json.loads(out.getvalue())['status'],'refused')

    def test_preview_does_not_create_directory_or_execute(self):
        self.assertFalse(pilot.preview(self.root,self.image)['executed'])
        self.assertFalse(self.root.exists())

    def test_prepare_never_overwrites_and_never_claims_observed(self):
        self.assertFalse(pilot.prepare(self.root,self.image)['runtime_observed'])
        with self.assertRaises(FileExistsError):pilot.prepare(self.root,self.image)
        self.refused()

    def test_only_explicit_local_image_ids(self):
        for image in ['python:latest','python@sha256:'+'1'*64,'sha256:short',None]:
            with self.assertRaises(ValueError):pilot.preview(self.root,image)

    def test_validated_reports_are_labelled_self_attested(self):
        self.fixture()
        result=pilot.validate(self.root)
        self.assertEqual(result['status'],'synthetic_evidence_validated')
        self.assertEqual(result['runtime_observed'],'reported_by_local_receipt')

    def test_commands_have_no_pull_remote_context_or_broad_mount(self):
        pilot.prepare(self.root,self.image)
        commands=json.loads((self.root/'commands.json').read_text())
        run=commands['run']
        self.assertIn('--pull=never',run)
        self.assertIn('--network=none',run)
        self.assertEqual(run.count('--mount'),2)
        self.assertIn(str(self.root/'docker-config'),run)
        self.assertEqual(commands['container_inspect'][-1],commands['cleanup_after_inspection'][-1])

    def test_missing_failed_or_stale_probe_evidence_refused(self):
        original,container=self.fixture()
        for mutation in [{'nonce':'0'*32},{'schema':True},{'checks':{}},
                         {'checks':{**original['checks'],'other_client_unreadable':False}},
                         {'checks':{**original['checks'],'input_readonly':1}}]:
            self.save_report({**original,**mutation},container);self.refused()

    def test_runtime_policy_failures_and_wrong_types_refused(self):
        result,original=self.fixture()
        changes=[('NetworkMode','host'),('ReadonlyRootfs',False),('Privileged',True),
                 ('CapDrop',[]),('SecurityOpt',['seccomp=unconfined']),('Memory',True),
                 ('NanoCpus',0),('PidsLimit',100),('Devices',[{}]),('PidMode','host'),
                 ('Tmpfs',{'/tmp':'rw'}),('Tmpfs',{'/tmp':True})]
        for key,value in changes:
            container=copy.deepcopy(original);container['HostConfig'][key]=value
            self.save_report(result,container);self.refused()
        container=copy.deepcopy(original);container['State']['ExitCode']=False
        self.save_report(result,container);self.refused()

    def test_environment_or_extra_mounts_refused(self):
        result,original=self.fixture()
        for env in [[{'invalid':'object'}],['API_KEY=synthetic-only'],['ISOLATION_PILOT_CREDENTIAL=synthetic-only']]:
            container=copy.deepcopy(original);container['Config']['Env']=env
            self.save_report(result,container);self.refused()
        container=copy.deepcopy(original);container['Mounts'].append({'Destination':'/host','Source':'/','RW':False,'Type':'bind'})
        self.save_report(result,container);self.refused()
        container=copy.deepcopy(original);container['Mounts'][0]['RW']=0
        self.save_report(result,container);self.refused()

    def test_changed_fixture_or_commands_or_copied_scope_refused(self):
        self.fixture()
        target=Path(self.temp.name)/'copied'
        shutil.copytree(self.root,target)
        with self.assertRaises(ValueError):pilot.validate(target)
        path=self.root/'commands.json';old=path.read_bytes();path.write_text('{}')
        self.refused();path.write_bytes(old)
        (self.root/'client-b/canary.txt').write_text('changed synthetic canary')
        self.refused()


if __name__ == '__main__':unittest.main()
