import ctypes
import os
import sys
import unittest
from unittest.mock import patch
from shiboken6 import VoidPtr

if sys.platform != 'win32':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer
from projectscope.windows import native


class FakeWin32:
    """Model the external registration resource on hosts without Win32."""

    def __init__(self):
        self.registered = {}
        self.blocked = set()

    def register(self, identifier, modifiers, key):
        combo = (modifiers & ~0x4000, key)
        if combo in self.blocked or combo in self.registered.values():
            raise OSError(1409, 'Hot key is already registered')
        if not modifiers & 0x4000:
            raise AssertionError('Registration must suppress auto-repeat')
        self.registered[identifier] = combo

    def unregister(self, identifier):
        del self.registered[identifier]


class NativeHotkeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.backend = FakeWin32()
        self.calls = []
        with patch.object(native, '_create_backend', return_value=self.backend):
            self.hotkeys = native.NativeHotkeys(self.app, {
                'toggle': lambda: self.calls.append('toggle'),
                'next': lambda: self.calls.append('next'),
            })
        self.addCleanup(self.hotkeys.close)

    def dispatch(self, identifier, modifiers=6, key=0x7A, event=b'windows_dispatcher_MSG'):
        message = native.MSG()
        message.message = 0x0312
        message.wParam = identifier
        message.lParam = modifiers | key << 16
        return self.hotkeys.nativeEventFilter(event, ctypes.addressof(message))

    def test_register_dispatch_and_close_release_resources(self):
        self.assertEqual(self.hotkeys.register({'toggle': 'Ctrl+Shift+F11'}), {})
        identifier = next(iter(self.backend.registered))
        self.assertEqual(self.dispatch(identifier), (True, 0))
        self.assertEqual(self.calls, ['toggle'])
        self.assertEqual(self.dispatch(identifier, event=b'xcb_generic_event_t'), (False, 0))
        self.assertEqual(self.dispatch(identifier, key=0x79), (False, 0))
        self.assertEqual(self.dispatch(identifier + 100), (False, 0))
        self.hotkeys.close()
        self.hotkeys.close()
        self.assertEqual(self.hotkeys.active_bindings, {})
        self.assertEqual(self.backend.registered, {})
        self.assertEqual(self.dispatch(identifier), (False, 0))
        self.assertIn('toggle', self.hotkeys.register({'toggle': 'Home'}))

    def test_qt_void_pointer_dispatch_does_not_depend_on_buffer_length(self):
        self.assertEqual(self.hotkeys.register({'toggle': 'Ctrl+Shift+F11'}), {})
        message = native.MSG()
        message.message = 0x0312
        message.wParam = next(iter(self.backend.registered))
        message.lParam = 6 | 0x7A << 16
        # PySide passes void* native messages as VoidPtr, not Python integers.
        # Its bool() checks buffer size, so a valid zero-size pointer is false
        # and an unknown-size pointer raises IndexError.
        for size in (0, -1):
            with self.subTest(size=size):
                pointer = VoidPtr(ctypes.addressof(message), size)
                self.assertEqual(self.hotkeys.nativeEventFilter(b'windows_generic_MSG', pointer), (True, 0))
        self.assertEqual(self.calls, ['toggle', 'toggle'])
        self.assertEqual(self.hotkeys.nativeEventFilter(b'windows_generic_MSG', VoidPtr(0, 0)), (False, 0))
        self.assertEqual(self.hotkeys.nativeEventFilter(b'windows_generic_MSG', None), (False, 0))

    def test_invalid_or_duplicate_mapping_leaves_active_shortcuts_working(self):
        self.hotkeys.register({'toggle': 'Home'})
        errors = self.hotkeys.register({'toggle': 'Ctrl+A', 'next': 'Control+A'})
        self.assertEqual(set(errors), {'toggle', 'next'})
        self.assertEqual(self.hotkeys.active_bindings, {'toggle': 'Home'})
        self.assertIn('toggle', self.hotkeys.register({'toggle': 'F12'}))
        self.assertIn('missing', self.hotkeys.register({'missing': 'F1'}))
        self.assertEqual(self.hotkeys.active_bindings, {'toggle': 'Home'})

    def test_conflict_restores_previous_mapping_and_reports_failed_action(self):
        self.hotkeys.register({'toggle': 'Home', 'next': 'End'})
        self.backend.blocked.add((0, 0x70))
        errors = self.hotkeys.register({'toggle': 'F1', 'next': 'F2'})
        self.assertIn('toggle', errors)
        self.assertIn('1409', errors['toggle'])
        self.assertEqual(self.hotkeys.active_bindings, {'toggle': 'Home', 'next': 'End'})
        identifier = next(i for i, combo in self.backend.registered.items() if combo == (0, 0x24))
        self.dispatch(identifier, 0, 0x24)
        self.assertEqual(self.calls, ['toggle'])

    def test_rollback_failure_is_reported_and_actual_bindings_are_honest(self):
        self.hotkeys.register({'toggle': 'Home'})
        self.backend.blocked.update({(0, 0x24), (0, 0x70)})
        errors = self.hotkeys.register({'toggle': 'F1'})
        self.assertIn('restore', errors['toggle'].lower())
        self.assertEqual(self.hotkeys.active_bindings, {})

    def test_swapping_keys_and_disabling_actions_updates_actual_mapping(self):
        self.hotkeys.register({'toggle': 'Home', 'next': 'End'})
        self.assertEqual(self.hotkeys.register({'toggle': 'End', 'next': 'Home'}), {})
        self.assertEqual(self.hotkeys.active_bindings, {'toggle': 'End', 'next': 'Home'})
        self.assertEqual(self.hotkeys.register({'toggle': '', 'next': 'Home'}), {})
        self.assertEqual(self.hotkeys.active_bindings, {'next': 'Home'})
        self.assertEqual(set(self.backend.registered.values()), {(0, 0x24)})

    @unittest.skipIf(sys.platform == 'win32', 'Non-Windows fallback')
    def test_non_windows_does_not_claim_native_registration(self):
        hotkeys = native.NativeHotkeys(self.app, {'toggle': lambda: None})
        self.addCleanup(hotkeys.close)
        self.assertIn('unavailable', hotkeys.register({'toggle': 'Home'})['toggle'].lower())
        self.assertEqual(hotkeys.active_bindings, {})
        self.assertEqual(hotkeys.register({'toggle': ''}), {})


@unittest.skipUnless(sys.platform == 'win32', 'Requires actual Windows desktop APIs')
class WindowsNativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_real_registration_release_reregister_and_filter_dispatch(self):
        calls = []
        first = native.NativeHotkeys(self.app, {'toggle': lambda: calls.append('toggle')})
        self.addCleanup(first.close)
        self.assertEqual(first.register({'toggle': 'Ctrl+Shift+F11'}), {})
        second = native.NativeHotkeys(self.app, {'toggle': lambda: None})
        self.addCleanup(second.close)
        self.assertIn('toggle', second.register({'toggle': 'Ctrl+Shift+F11'}))
        identifier = first._ids['toggle']
        message = native.MSG()
        message.message = 0x0312
        message.wParam = identifier
        message.lParam = 6 | 0x7A << 16
        self.assertEqual(first.nativeEventFilter(b'windows_dispatcher_MSG', ctypes.addressof(message)), (True, 0))
        self.assertEqual(calls, ['toggle'])
        # Send only this application's WM_HOTKEY notification to its own
        # thread, never synthesize keyboard input. This exercises Qt's actual
        # native filter bridge in addition to the ctypes struct dispatch.
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.GetCurrentThreadId.restype = ctypes.c_uint32
        user32 = first._backend.user32
        user32.PostThreadMessageW.argtypes = [ctypes.c_uint32, ctypes.c_uint32,
                                              ctypes.c_size_t, ctypes.c_ssize_t]
        user32.PostThreadMessageW.restype = ctypes.c_int
        self.app.processEvents()
        self.assertTrue(user32.PostThreadMessageW(kernel32.GetCurrentThreadId(),
                                                 0x0312, identifier, 6 | 0x7A << 16))
        loop = QEventLoop()
        QTimer.singleShot(50, loop.quit)
        loop.exec()
        self.assertEqual(calls, ['toggle', 'toggle'])
        first.close()
        self.assertEqual(second.register({'toggle': 'Ctrl+Shift+F11'}), {})


if __name__ == '__main__':
    unittest.main()
