"""Win32 global hotkeys dispatched through Qt, with honest conflict reporting.

All construction, registration, and cleanup must run on the Qt application
thread: RegisterHotKey(NULL, ...) registers with the calling thread.
"""

import ctypes
import itertools
import logging
import sys
from collections.abc import Callable, Mapping

from PySide6.QtCore import QAbstractNativeEventFilter

from .hotkeys import parse_binding

MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
_LOG = logging.getLogger(__name__)
_IDENTIFIERS = itertools.count(0x4000)


class _POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_int32), ('y', ctypes.c_int32)]


class MSG(ctypes.Structure):
    # Fixed-width Windows DWORD/LONG types also make off-platform tests valid.
    _fields_ = [('hwnd', ctypes.c_void_p), ('message', ctypes.c_uint32),
                ('wParam', ctypes.c_size_t), ('lParam', ctypes.c_ssize_t),
                ('time', ctypes.c_uint32), ('pt', _POINT),
                ('lPrivate', ctypes.c_uint32)]


class _Win32Backend:
    def __init__(self):
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                               ctypes.c_uint, ctypes.c_uint]
        self.user32.RegisterHotKey.restype = ctypes.c_int
        self.user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.user32.UnregisterHotKey.restype = ctypes.c_int

    def register(self, identifier, modifiers, key):
        if not self.user32.RegisterHotKey(None, identifier, modifiers, key):
            raise ctypes.WinError(ctypes.get_last_error())

    def unregister(self, identifier):
        if not self.user32.UnregisterHotKey(None, identifier):
            raise ctypes.WinError(ctypes.get_last_error())


def _create_backend():
    return _Win32Backend() if sys.platform == 'win32' else None


class NativeHotkeys(QAbstractNativeEventFilter):
    """Own a retained native event filter and a set of thread hotkeys.

    register() replaces the complete mapping. Invalid mappings leave existing
    shortcuts untouched. Runtime conflicts roll back changes, retaining
    unchanged bindings throughout. Restoration can itself lose a race with
    another process; errors explicitly report that and active_bindings always
    describes the actual active mapping (disabled actions are omitted).
    """

    def __init__(self, app, callbacks: Mapping[str, Callable[[], None]]):
        super().__init__()
        self._app = app
        self._callbacks = dict(callbacks)
        self._backend = _create_backend()
        self._active = {}
        self._ids = {}
        self._closed = False
        self.cleanup_errors = {}
        app.installNativeEventFilter(self)
        app.aboutToQuit.connect(self.close)

    @property
    def active_bindings(self) -> dict[str, str]:
        return {action: binding for action, (binding, _) in self._active.items()}

    def _remove(self, action, errors):
        try:
            self._backend.unregister(self._ids[action])
        except OSError as exc:
            errors[action] = f'Could not release shortcut: {exc}'
            return False
        del self._active[action]
        return True

    def _add(self, action, value):
        if action not in self._ids:
            identifier = next(_IDENTIFIERS)
            if identifier > 0xBFFF:
                raise OSError('Application hotkey identifier range exhausted.')
            self._ids[action] = identifier
        binding, (modifiers, key) = value
        self._backend.register(self._ids[action], modifiers | MOD_NOREPEAT, key)
        self._active[action] = (binding, (modifiers, key))

    def register(self, mapping: Mapping[str, str]) -> dict[str, str]:
        errors = {}
        desired = {}
        owners = {}
        for action, binding in mapping.items():
            if self._closed:
                errors[action] = 'Global shortcut manager is closed.'
                continue
            if action not in self._callbacks or not callable(self._callbacks[action]):
                errors[action] = 'No callback is available for this action.'
                continue
            try:
                combo = parse_binding(binding)
            except ValueError as exc:
                errors[action] = str(exc)
                continue
            if combo is None:
                continue
            if combo in owners:
                other = owners[combo]
                errors[action] = f'Shortcut is also assigned to {other}.'
                errors[other] = f'Shortcut is also assigned to {action}.'
            owners[combo] = action
            desired[action] = (binding.strip(), combo)
        if errors:
            return errors
        if self._backend is None:
            return {action: 'Global shortcuts are unavailable outside Windows.' for action in desired}

        previous = dict(self._active)
        changed = {action for action in previous.keys() | desired.keys()
                   if previous.get(action) != desired.get(action)}
        for action in list(self._active):
            if action in changed:
                self._remove(action, errors)
        if not errors:
            for action, value in desired.items():
                if action in changed:
                    try:
                        self._add(action, value)
                    except OSError as exc:
                        errors[action] = f'Could not register shortcut: {exc}'
        if not errors:
            return {}

        # Undo successful new registrations before restoring the old mapping.
        for action in list(self._active):
            if action in changed and self._active[action] != previous.get(action):
                self._remove(action, errors)
        for action, value in previous.items():
            if action not in self._active:
                try:
                    self._add(action, value)
                except OSError as exc:
                    errors[action] = errors.get(action, '') + f' Could not restore previous shortcut: {exc}'
        for action in changed:
            if self._active.get(action) != desired.get(action):
                errors.setdefault(action, 'Shortcut mapping was not applied because another shortcut failed.')
        return errors

    def nativeEventFilter(self, eventType, message):
        if self._closed or bytes(eventType) not in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            return False, 0
        if not message:
            return False, 0
        msg = MSG.from_address(int(message))
        if msg.message != WM_HOTKEY:
            return False, 0
        for action, (_, combo) in tuple(self._active.items()):
            if self._ids[action] == msg.wParam and combo == (msg.lParam & 0xFFFF, (msg.lParam >> 16) & 0xFFFF):
                try:
                    self._callbacks[action]()
                except Exception:
                    _LOG.exception('Global shortcut callback failed: %s', action)
                return True, 0
        return False, 0

    def close(self):
        """Release registrations; safe to call repeatedly and on aboutToQuit."""
        if not self._closed:
            self._closed = True
            self._app.removeNativeEventFilter(self)
            self._app.aboutToQuit.disconnect(self.close)
        self.cleanup_errors = {}
        for action in list(self._active):
            self._remove(action, self.cleanup_errors)
        for action, error in self.cleanup_errors.items():
            _LOG.error('%s: %s', action, error)
