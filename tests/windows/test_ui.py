"""Offscreen Qt behavior checks, independent of a real Windows desktop."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from projectscope.profiles import load_profile

ROOT = Path(__file__).resolve().parents[2]
APP = QApplication.instance() or QApplication([])

class PaintingTests(unittest.TestCase):
    def test_overlapping_components_apply_opacity_once(self):
        from projectscope.windows.painting import render_image
        style = load_profile(ROOT / 'presets/fps-balanced.json')['style']
        style.update(opacity=0.5, outline_width=2)
        style['lines']['gap'] = 0
        image = render_image(style, 100, 100)
        self.assertAlmostEqual(image.pixelColor(50, 50).alpha(), 128, delta=1)
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)

    def test_rotation_scale_and_outline_preserve_bounds(self):
        from projectscope.windows.painting import render_image
        from projectscope.render import extent
        style = load_profile(ROOT / 'presets/fps-balanced.json')['style']
        style.update(rotation=45, scale=3, outline_width=5)
        image = render_image(style)
        self.assertGreaterEqual(image.width(), 2 * extent(style))
        self.assertTrue(any(image.pixelColor(x, image.height() // 2).alpha() for x in range(image.width())))
        self.assertTrue(all(image.pixelColor(x, 0).alpha() == 0 for x in range(image.width())))

class EditorTests(unittest.TestCase):
    def setUp(self):
        from projectscope.windows.state import State
        from projectscope.windows.ui import Editor
        self.tmp = tempfile.TemporaryDirectory()
        self.state = State(ROOT / 'presets', Path(self.tmp.name))
        self.editor = Editor(self.state, ROOT)
        self.editor.show()
        APP.processEvents()

    def tearDown(self):
        self.editor.shutdown()
        self.editor.deleteLater()
        APP.processEvents()
        self.tmp.cleanup()

    def test_shape_control_updates_state_and_preview(self):
        self.editor.controls['lines.length'].setValue(37)
        self.assertEqual(self.state.profile['style']['lines']['length'], 37)
        self.assertEqual(self.editor.preview.style['lines']['length'], 37)

    def test_catalog_selection_preserves_visibility(self):
        self.state.set_option('visible', False)
        self.editor.preset_list.setCurrentRow(3)
        self.assertFalse(self.state.visible)
        self.assertEqual(self.state.profile['id'], self.editor.preset_list.currentItem().data(Qt.ItemDataRole.UserRole)['id'])

    def test_offset_and_overlay_input_contract(self):
        self.editor.offset_x.setValue(24)
        self.assertEqual(self.state.offset_x, 24)
        flags = self.editor.overlay.windowFlags()
        self.assertTrue(flags & Qt.WindowType.WindowTransparentForInput)
        self.assertTrue(flags & Qt.WindowType.WindowDoesNotAcceptFocus)
        self.assertTrue(self.editor.overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        screen = APP.primaryScreen().geometry()
        self.assertAlmostEqual(self.editor.overlay.geometry().center().x(), screen.center().x() + 24, delta=1)

    def test_import_rejects_malformed_profile_without_state_change(self):
        original = copy.deepcopy(self.state.profile)
        path = Path(self.tmp.name) / 'broken.json'
        path.write_text('{"schema_version": 999}')
        with self.assertRaises(ValueError):
            self.editor.import_profile(path)
        self.assertEqual(self.state.profile, original)

    def test_export_round_trips_strict_portable_profile(self):
        path = Path(self.tmp.name) / 'export.json'
        self.editor.export_profile(path)
        self.assertEqual(load_profile(path), self.state.profile)

    def test_missing_monitor_falls_back_to_primary(self):
        self.state.set_option('monitor', 63)
        area = APP.primaryScreen().geometry()
        self.assertAlmostEqual(self.editor.overlay.geometry().center().x(), area.center().x(), delta=1)
        self.assertEqual(self.editor.monitor.currentData(), -1)

    def test_swapping_shortcuts_commits_as_one_mapping(self):
        mapping = self.state.hotkeys
        mapping['next'], mapping['previous'] = mapping['previous'], mapping['next']
        self.editor.set_hotkeys(mapping)
        self.assertEqual(self.state.hotkeys, mapping)

    def test_invalid_last_shortcut_does_not_partially_save(self):
        before = self.state.hotkeys
        mapping = dict(before)
        mapping['toggle'] = 'Ctrl+Alt+Q'
        mapping['thickness_down'] = 'NotAKey'
        with self.assertRaises(ValueError):
            self.editor.set_hotkeys(mapping)
        self.assertEqual(self.state.hotkeys, before)

    def test_save_hotkey_saves_current_name_without_opening_dialog(self):
        from unittest.mock import patch
        self.editor.hide()
        with patch('projectscope.windows.ui.QInputDialog.getText', side_effect=AssertionError('Unexpected save dialog')):
            self.editor.hotkey_callbacks()['save']()
        self.assertFalse(self.editor.isVisible())
        personal = list((Path(self.tmp.name) / 'presets').glob('*.json'))
        self.assertEqual(len(personal), 1)
        self.assertEqual(load_profile(personal[0])['name'], self.state.profile['name'])

    def test_background_save_failure_reports_without_modal_or_focus(self):
        from unittest.mock import patch
        self.editor.hide()
        with patch('projectscope.profiles.os.replace', side_effect=PermissionError('Disk write denied')):
            with patch('projectscope.windows.ui.QMessageBox.warning', side_effect=AssertionError('Unexpected modal error')):
                self.editor.hotkey_callbacks()['save']()
        self.assertFalse(self.editor.isVisible())
        self.assertIsNone(APP.activeModalWidget())
        self.assertIn('Disk write denied', self.editor.status.text())
        self.editor.sync()
        self.assertIn('Disk write denied', self.editor.status.text())

    def test_hotkey_conflict_restores_persisted_binding(self):
        old = self.state.hotkeys['toggle']
        class Manager:
            active_bindings = {}
            def register(self, mapping):
                if mapping['toggle'] == 'Ctrl+Alt+Q':
                    return {'toggle': 'Already in use'}
                self.active_bindings = dict(mapping)
                return {}
            def close(self): pass
        manager = Manager()
        self.editor.bind_hotkeys(manager)
        with self.assertRaisesRegex(ValueError, 'Already in use'):
            self.editor.set_hotkey('toggle', 'Ctrl+Alt+Q')
        self.assertEqual(self.state.hotkeys['toggle'], old)
        self.assertEqual(manager.active_bindings['toggle'], old)
        from projectscope.windows.state import State
        restored = State(ROOT / 'presets', Path(self.tmp.name))
        self.assertEqual(restored.hotkeys['toggle'], old)

    def test_close_hides_to_tray_when_available(self):
        from PySide6.QtGui import QCloseEvent
        self.editor.tray_available = True
        event = QCloseEvent()
        self.editor.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertFalse(self.editor.isVisible())
        self.assertFalse(self.editor._closed)
        self.editor.reopen()
        self.assertTrue(self.editor.isVisible())

    def test_close_without_tray_shuts_down_overlay(self):
        from PySide6.QtGui import QCloseEvent
        self.editor.tray_available = False
        event = QCloseEvent()
        self.editor.closeEvent(event)
        self.assertTrue(event.isAccepted())
        self.assertFalse(self.editor.overlay.isVisible())

    def test_shutdown_closes_hotkeys_once_and_hides_overlay(self):
        class Manager:
            closed = 0
            def register(self, mapping): return {}
            def close(self): self.closed += 1
        manager = Manager()
        self.editor.bind_hotkeys(manager)
        self.editor.shutdown()
        self.editor.shutdown()
        self.assertEqual(manager.closed, 1)
        self.assertFalse(self.editor.overlay.isVisible())

if __name__ == '__main__':
    unittest.main()
