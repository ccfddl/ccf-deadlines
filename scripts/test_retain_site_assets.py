import json
import tempfile
import unittest
from pathlib import Path

from retain_site_assets import MANIFEST, retain_assets


class RetainedAssetTests(unittest.TestCase):
    def test_preserves_previous_module_dependencies_without_copying_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous, output = root / 'previous', root / 'output'
            previous.mkdir()
            output.mkdir()
            files = ['app-old.js', 'app-old_bg.wasm', 'styles-old.css',
                     'snippets/old/inline0.js', 'conferences/app-old.js',
                     'conferences/style-old.css', 'conferences/app.js']
            for name in [*files, 'index.html', 'conferences/ai/acl/index.html', 'CNAME']:
                path = previous / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
            self.assertEqual(retain_assets(output, previous, now=100), len(files))
            for name in files:
                self.assertEqual((output / name).read_text(), name)
            self.assertFalse((output / 'index.html').exists())
            self.assertFalse((output / 'CNAME').exists())
            self.assertFalse((output / 'conferences/ai/acl/index.html').exists())

    def test_expiration_does_not_overwrite_current_assets_or_extend_old_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous, output = root / 'previous', root / 'output'
            previous.mkdir()
            output.mkdir()
            for name in ['expired.js', 'recent.js', 'styles-current.css']:
                (previous / name).write_text('previous')
            (previous / MANIFEST).write_text(json.dumps({
                'expired.js': 0, 'recent.js': 90000, 'styles-current.css': 0,
            }))
            (output / 'styles-current.css').write_text('current')
            self.assertEqual(retain_assets(output, previous, now=100000), 1)
            self.assertFalse((output / 'expired.js').exists())
            self.assertEqual((output / 'styles-current.css').read_text(), 'current')
            metadata = json.loads((output / MANIFEST).read_text())
            self.assertEqual(metadata['recent.js'], 90000)
            self.assertEqual(metadata['styles-current.css'], 100000)
            next_output = root / 'next'
            next_output.mkdir()
            retain_assets(next_output, output, now=180000)
            self.assertFalse((next_output / 'recent.js').exists())

    def test_symlinks_are_not_copied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous, output = root / 'previous', root / 'output'
            previous.mkdir()
            output.mkdir()
            private = root / 'private.css'
            private.write_text('private')
            (previous / 'linked.css').symlink_to(private)
            self.assertEqual(retain_assets(output, previous, now=100), 0)
            self.assertFalse((output / 'linked.css').exists())


if __name__ == '__main__':
    unittest.main()
