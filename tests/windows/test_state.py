import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class WindowsState(unittest.TestCase):
    def setUp(self):
        from projectscope.windows.state import State
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        self.state = State(ROOT / 'presets', self.data)

    def test_invalid_edit_preserves_memory_and_file(self):
        self.state.set_option('visible', False)
        original = copy.deepcopy(self.state.profile)
        disk = (self.data / 'settings.json').read_bytes()
        bad = copy.deepcopy(original); bad['style']['opacity'] = 3
        with self.assertRaises(ValueError): self.state.update_profile(bad)
        self.assertEqual(self.state.profile, original)
        self.assertEqual((self.data / 'settings.json').read_bytes(), disk)

    def test_disk_failure_does_not_accept_edit(self):
        with patch('os.replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError): self.state.set_option('visible', False)
        self.assertTrue(self.state.visible)
        self.assertFalse((self.data / 'settings.json').exists())

    def test_cycle_and_randomize_preserve_visibility_and_opacity(self):
        self.state.set_option('visible', False)
        first = self.state.profile['id']
        self.state.cycle(1)
        self.assertNotEqual(self.state.profile['id'], first)
        self.state.cycle(-1)
        self.assertEqual(self.state.profile['id'], first)
        profile = copy.deepcopy(self.state.profile); profile['style']['opacity'] = 0
        self.state.update_profile(profile)
        for _ in range(10): self.state.randomize()
        self.assertFalse(self.state.visible)
        self.assertEqual(self.state.profile['style']['opacity'], 0)

    def test_persisted_configuration_and_personal_preset_roundtrip(self):
        from projectscope.windows.state import State
        self.state.set_option('offset_x', -35)
        self.state.set_option('monitor', 2)
        self.state.save_preset('My crosshair')
        restored = State(ROOT / 'presets', self.data)
        self.assertEqual(restored.offset_x, -35)
        self.assertEqual(restored.monitor, 2)
        self.assertEqual(restored.profile['name'], 'My crosshair')
        self.assertEqual(len(restored.catalog()), 31)

    def test_corrupt_preferences_are_preserved_before_replacement(self):
        from projectscope.windows.state import State
        broken = b'{broken preferences'
        (self.data / 'settings.json').write_bytes(broken)
        state = State(ROOT / 'presets', self.data)
        self.assertTrue(state.warning)
        self.assertEqual((self.data / 'settings.json').read_bytes(), broken)
        state.set_option('visible', False)
        backups = list(self.data.glob('settings.invalid-*.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), broken)
        self.assertFalse(json.loads((self.data / 'settings.json').read_text())['visible'])

    def test_canonical_duplicate_shortcut_is_rejected(self):
        self.state.set_hotkey('toggle', 'Ctrl+F8')
        with self.assertRaises(ValueError): self.state.set_hotkey('random', 'Control+F8')
        self.state.set_hotkey('random', '')
        self.assertEqual(self.state.hotkeys['random'], '')

    def test_hotkeys_can_be_swapped_atomically(self):
        bindings = self.state.hotkeys
        bindings['toggle'], bindings['random'] = bindings['random'], bindings['toggle']
        self.state.set_hotkeys(bindings)
        self.assertEqual(self.state.hotkeys['toggle'], 'Pause')
        self.assertEqual(self.state.hotkeys['random'], 'Home')
        previous = self.state.hotkeys
        bindings['save'] = 'F12'
        with self.assertRaises(ValueError): self.state.set_hotkeys(bindings)
        self.assertEqual(self.state.hotkeys, previous)

    def test_mutations_respect_profile_bounds(self):
        for _ in range(40): self.state.resize(1)
        self.assertEqual(self.state.profile['style']['scale'], 8)
        self.state.set_option('visible', False)
        before = copy.deepcopy(self.state.profile['style'])
        self.state.cycle_color()
        after = self.state.profile['style']
        self.assertEqual(after['lines'], before['lines'])
        self.assertEqual(after['opacity'], before['opacity'])
        self.assertFalse(self.state.visible)
