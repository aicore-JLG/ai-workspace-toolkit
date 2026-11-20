import hashlib
import io
import importlib.util
import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest import mock

spec = importlib.util.spec_from_file_location('integrations', Path(__file__).resolve().parents[1] / 'tools/integrations.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'integrations/vendor/demo/skills/example/SKILL.md'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('---\nname: example\n---\nDo something useful.\n')
        self.entry = {'id':'demo','repository':'example/demo','commit':'a'*40,'kind':'bundle','bundled_paths':['skills/example'],'license':'MIT','source':'https://github.com/example/demo','purpose':'demo','executable':None}
        (self.root/'integrations/catalog.json').write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        self.lock()

    def tearDown(self): self.tmp.cleanup()
    def lock(self):
        (self.root/'integrations/bundles.lock.json').write_text(json.dumps({'schema_version':1,'files':[{'integration':'demo','path':self.source.relative_to(self.root).as_posix(),'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}]}))

    def accept_source(self):
        from skill_review import scan,attest
        result=scan(self.root,'demo','example')
        attest(self.root,'demo','example',result['fingerprint'],
            [f['id'] for f in result['findings']], 'synthetic-test-reviewer',
            'Inspected the fixture: a single inert example instruction.')

    def test_preview_has_no_writes_then_activation_copies_assets(self):
        before = sorted(str(p) for p in self.root.rglob('*'))
        self.assertFalse(m.activate(self.root,'demo','example')['written'])
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob('*')))
        self.accept_source()
        result=m.activate(self.root,'demo','example',write=True)
        self.assertTrue(result['written'])
        self.assertEqual((self.root/'.claude/skills/example/SKILL.md').read_bytes(), self.source.read_bytes())

    def test_changed_source_rejected(self):
        self.source.write_text('changed')
        with self.assertRaises(ValueError):m.activate(self.root,'demo','example',write=True)
        self.assertFalse((self.root/'.claude').exists())

    def test_unlocked_extra_source_rejected(self):
        self.source.with_name('surprise.py').write_text('print(1)')
        with self.assertRaises(ValueError):m.activate(self.root,'demo','example',write=True)

    def test_existing_skill_preserved(self):
        dest=self.root/'.claude/skills/example/SKILL.md'
        dest.parent.mkdir(parents=True); dest.write_text('my work')
        with self.assertRaises(ValueError):m.activate(self.root,'demo','example',write=True)
        self.assertEqual(dest.read_text(),'my work')

    def test_paths_and_hosts_rejected(self):
        for skill in ['../outside','/absolute','x/y','..\\outside']:
            with self.assertRaises(ValueError):m.activate(self.root,'demo',skill,write=True)
        with self.assertRaises(ValueError):m.activate(self.root,'demo','example',host='../../outside',write=True)

    def test_codex_destination_is_project_local(self):
        self.accept_source()
        m.activate(self.root,'demo','example',host='codex',write=True)
        self.assertTrue((self.root/'.agents/skills/example/SKILL.md').exists())

    def test_activation_requires_current_source_review(self):
        with self.assertRaises(ValueError):m.activate(self.root,'demo','example',write=True)
        self.accept_source()
        self.source.write_text('A changed but newly integrity-locked skill.')
        self.lock()
        with self.assertRaises(ValueError):m.activate(self.root,'demo','example',write=True)
        self.assertFalse((self.root/'.claude/skills/example').exists())

    def test_missing_bundle_is_not_valid(self):
        self.source.unlink()
        self.assertFalse(m.verify_bundles(self.root)['ok'])

    def test_doppler_requires_scope_and_names_and_disables_disk_fallback(self):
        cmd=m.doppler_command('my-app','dev',['python','app.py'],['API_KEY'])
        self.assertIn('--no-fallback',cmd)
        self.assertIn('--only-secrets',cmd)
        self.assertEqual(cmd[-3:],['--','python','app.py'])
        for project, config, names in [('', 'dev',['API_KEY']),('my-app','', ['API_KEY']),('my-app','dev',[]),('--token','dev',['API_KEY'])]:
            with self.assertRaises(ValueError):m.doppler_command(project,config,['python','app.py'],names)

    def test_npm_plan_pins_version_and_has_no_global_install(self):
        self.entry.update(kind='npm', package='demo-package', version='1.2.3',executable='demo',integrity='sha512-test')
        (self.root/'integrations/catalog.json').write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        plan=m.install_plan(self.root,'demo')
        self.assertIn('demo-package@1.2.3',plan['commands'][0])
        self.assertIn('--ignore-scripts',plan['commands'][0])
        self.assertNotIn('-g',plan['commands'][0])
        self.assertTrue(Path(plan['destination']).is_relative_to(self.root))

    def test_archive_escape_rejected_before_writing(self):
        for name in ['../outside.txt','/outside.txt','C:/outside.txt','a/../../outside','NUL.txt','..\\outside']:
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as z:
                z.writestr('safe.txt','safe')
                info=zipfile.ZipInfo(name);info.filename=name
                z.writestr(info,'bad')
            dest=self.root/'unpack';dest.mkdir(exist_ok=True)
            with self.assertRaises(ValueError):m.unpack_release(data.getvalue(),dest)
            self.assertEqual(list(dest.iterdir()),[])

    def test_valid_archive_and_duplicate_member_boundary(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('release/bin/tool.txt','hello')
        dest=self.root/'unpack';dest.mkdir()
        m.unpack_release(data.getvalue(),dest)
        self.assertEqual((dest/'release/bin/tool.txt').read_text(),'hello')
        with self.assertRaises(ValueError):m.unpack_release(data.getvalue(),dest)

    def test_python_constraints_remain_exact_package_versions(self):
        self.entry.update(kind='python',package='demo',requirement='demo @ git+https://github.com/example/demo.git@'+'a'*40,constraints=['anthropic==0.112.0'])
        path=self.root/'integrations/catalog.json'
        path.write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        self.assertIn('anthropic==0.112.0',m.install_plan(self.root,'demo')['commands'][1])
        self.entry['constraints']=['--index-url=https://example.com']
        path.write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        with self.assertRaises(ValueError):m.install_plan(self.root,'demo')

    def test_runtime_and_doppler_share_policy_limits_and_discard_secrets(self):
        limits={'timeout_seconds':3,'max_output_bytes':2048}
        with mock.patch.object(m,'execution_limits',return_value=limits), \
             mock.patch.object(m,'runtime_argv',return_value=[sys.executable,'task.py']), \
             mock.patch.object(m,'execute_trusted',return_value=({'status':'completed'},0)) as run:
            m.run_integration(self.root,'demo',['--help'])
            self.assertEqual(run.call_args.kwargs['timeout_seconds'],3)
            self.assertEqual(run.call_args.kwargs['max_output_bytes'],2048)
            self.assertEqual(run.call_args.kwargs['output_mode'],'redact')
        with mock.patch.object(m,'execution_limits',return_value=limits), \
             mock.patch.object(m.shutil,'which',return_value=sys.executable), \
             mock.patch.object(m,'execute_trusted',return_value=({'status':'completed'},0)) as run:
            m.run_doppler(self.root,'app','dev',['python','task.py'],['API_KEY'])
            self.assertEqual(run.call_args.kwargs['output_mode'],'discard')
            self.assertEqual(run.call_args.kwargs['timeout_seconds'],3)

    def test_npm_runtime_uses_native_node_not_command_shim(self):
        self.entry.update(kind='npm',package='demo-package',executable='demo')
        (self.root/'integrations/catalog.json').write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        base=self.root/'.workspace/tools/demo/node_modules/demo-package'
        base.mkdir(parents=True)
        (base/'package.json').write_text(json.dumps({'bin':{'demo':'bin/cli.js'}}))
        (base/'bin').mkdir();(base/'bin/cli.js').write_text('// synthetic')
        with mock.patch.object(m,'executable',return_value=str(base/'demo.cmd')), \
             mock.patch.object(m.shutil,'which',return_value=sys.executable):
            argv=m.runtime_argv(self.root,'demo',['a&b'])
        self.assertEqual(argv,[sys.executable,str(base/'bin/cli.js'),'a&b'])

    def test_npm_runtime_rejects_bin_entry_outside_package(self):
        self.entry.update(kind='npm',package='demo-package',executable='demo')
        (self.root/'integrations/catalog.json').write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        base=self.root/'.workspace/tools/demo/node_modules/demo-package';base.mkdir(parents=True)
        (base/'package.json').write_text(json.dumps({'bin':{'demo':'../../foreign.js'}}))
        with mock.patch.object(m,'executable',return_value=str(base/'demo.cmd')), \
             mock.patch.object(m.shutil,'which',return_value=sys.executable):
            with self.assertRaises(ValueError):m.runtime_argv(self.root,'demo',[])

    def test_install_subprocess_uses_shared_runner_and_does_not_mark_failure_ready(self):
        self.entry.update(kind='npm', package='demo-package', version='1.2.3',executable='demo',integrity='sha512-test')
        (self.root/'integrations/catalog.json').write_text(json.dumps({'schema_version':1,'integrations':[self.entry]}))
        with mock.patch.object(m,'execution_limits',return_value={'timeout_seconds':4,'max_output_bytes':2048}), \
             mock.patch.object(m,'native_package_manager',side_effect=lambda argv:argv), \
             mock.patch.object(m.shutil,'which',return_value=sys.executable), \
             mock.patch.object(m,'execute_trusted',return_value=({'status':'timed_out'},1)) as run:
            with self.assertRaises(ValueError):m.install(self.root,'demo',run=True)
        self.assertEqual(run.call_args.kwargs['timeout_seconds'],4)
        self.assertEqual(run.call_args.kwargs['output_mode'],'discard')
        self.assertFalse((self.root/'.workspace/tools/demo/_ready.json').exists())

    def test_generic_doppler_route_cannot_log_secret_values(self):
        with mock.patch.object(m,'execution_limits',return_value={'timeout_seconds':3,'max_output_bytes':2048}), \
             mock.patch.object(m,'runtime_argv',return_value=['doppler','secrets']), \
             mock.patch.object(m,'entry',return_value={'id':'doppler'}), \
             mock.patch.object(m,'execute_trusted',return_value=({},0)) as run:
            m.run_integration(self.root,'doppler',['secrets'])
        self.assertEqual(run.call_args.kwargs['output_mode'],'discard')

    def test_windows_import_paths_are_extended_and_idempotent(self):
        spec=importlib.util.spec_from_file_location('python_cli',Path(__file__).resolve().parents[1]/'tools/python_cli.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        transformed=cli.long_paths([str(self.root),''])
        self.assertTrue(all(p.startswith('\\\\?\\') for p in transformed))
        self.assertEqual(cli.long_paths(transformed),transformed)
        self.assertEqual(cli.long_paths(['\\\\server\\share\\tools']),['\\\\?\\UNC\\server\\share\\tools'])

if __name__=='__main__':unittest.main()
