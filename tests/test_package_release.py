import hashlib, importlib.util, json, tempfile, unittest, zipfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('package_release',Path(__file__).resolve().parents[1]/'tools/package_release.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'README.md').write_text('original')
        (self.root/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema_version':1,'files':[{'path':'README.md','sha256':hashlib.sha256(b'original').hexdigest()}]}))
    def tearDown(self):self.tmp.cleanup()
    def test_only_manifested_files_ship(self):
        (self.root/'.env').write_text('synthetic private')
        (self.root/'private-note.md').write_text('synthetic private')
        out=self.root/'kit.zip';m.package(self.root,out)
        with zipfile.ZipFile(out) as z:self.assertEqual(set(z.namelist()),{'README.md','RELEASE-MANIFEST.json'})
    def test_modified_source_refused_before_output(self):
        (self.root/'README.md').write_text('personalised')
        out=self.root/'kit.zip'
        with self.assertRaises(ValueError):m.package(self.root,out)
        self.assertFalse(out.exists())
    def test_existing_release_preserved(self):
        out=self.root/'kit.zip';out.write_bytes(b'previous')
        with self.assertRaises(FileExistsError):m.package(self.root,out)
        self.assertEqual(out.read_bytes(),b'previous')
