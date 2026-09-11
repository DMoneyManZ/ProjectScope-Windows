import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Runtime(unittest.TestCase):
    def test_smoke_report_write_failure_still_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'editor.json').mkdir()
            result = subprocess.run([sys.executable, '-m', 'projectscope.windows', '--smoke-test',
                                     '--output', str(root / 'editor.png'), '--data-dir', str(root / 'preferences')],
                                    cwd=ROOT, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                                    capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'preferences/instance.lock').exists())

    def test_smoke_launch_saves_editor_capture_and_exits_without_background_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'editor.png'
            result = subprocess.run([sys.executable, '-m', 'projectscope.windows', '--smoke-test',
                                     '--output', str(output), '--data-dir', str(root / 'preferences')],
                                    cwd=ROOT, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            report = json.loads(output.with_suffix('.json').read_text())
            self.assertTrue(report['passed'])
            self.assertEqual(report['presets'], 30)
            self.assertFalse((root / 'preferences/instance.lock').exists())

    @unittest.skipIf(sys.platform == 'win32', 'Normal Windows launch is supported')
    def test_regular_launch_rejects_unsupported_platform_before_creating_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'not-created'
            result = subprocess.run([sys.executable, '-m', 'projectscope.windows', '--data-dir', str(target)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())
