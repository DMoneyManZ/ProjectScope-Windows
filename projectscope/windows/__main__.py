"""Launch the Windows application or perform a bounded UI smoke check."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description='ProjectScope-Windows crosshair studio')
    parser.add_argument('--smoke-test', action='store_true', help='render a stock editor test and exit')
    parser.add_argument('--output', type=Path, help='PNG path for the smoke-test editor screenshot')
    parser.add_argument('--data-dir', type=Path, help='alternate preferences directory')
    args = parser.parse_args()
    if sys.platform != 'win32' and not args.smoke_test:
        parser.error('This backend is for Windows. Use the GNOME application on Linux.')
    if args.smoke_test and (not args.output or not args.data_dir):
        parser.error('--smoke-test requires --output and --data-dir to isolate test data')

    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox
    from projectscope.windows.state import State
    from projectscope.windows.ui import Editor
    from projectscope.windows.native import NativeHotkeys

    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('io.projectscope.Crosshair.Windows')
    app = QApplication([sys.argv[0]])
    app.setApplicationName('ProjectScope-Windows')
    app.setOrganizationName('ProjectScope')
    app.setQuitOnLastWindowClosed(False)
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    app.setWindowIcon(QIcon(str(root / 'assets/projectscope.svg')))
    data = args.data_dir or Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'ProjectScope'
    data.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data / 'instance.lock'))
    if not lock.tryLock(0):
        if not args.smoke_test:
            QMessageBox.information(None, 'ProjectScope is already running',
                                    'Open ProjectScope from its crosshair icon in the system tray.')
        return 1
    editor = manager = None
    try:
        state = State(root / 'presets', data)
        editor = Editor(state, root)
        manager = NativeHotkeys(app, editor.hotkey_callbacks())
        editor.bind_hotkeys(manager)
        app.aboutToQuit.connect(editor.shutdown)
        editor.show()
        if args.smoke_test:
            def finish():
                report = {'platform': sys.platform, 'qt_platform': app.platformName(), 'presets': len(state.catalog()),
                          'editor_visible': editor.isVisible(), 'profile': state.profile['id']}
                try:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    if not editor.grab().save(str(args.output)):
                        raise RuntimeError('Editor screenshot could not be saved')
                    report['screenshot_saved'] = True
                    report['hotkeys_active'] = sorted(manager.active_bindings)
                    if sys.platform == 'win32' and app.platformName() == 'windows':
                        import ctypes
                        fn = ctypes.windll.user32.GetWindowLongW
                        fn.argtypes = [ctypes.c_void_p, ctypes.c_int]; fn.restype = ctypes.c_long
                        style = fn(int(editor.overlay.winId()), -20)
                        report['native_overlay_style'] = style
                        report['click_through'] = bool(style & 0x20)
                        report['no_activate'] = bool(style & 0x08000000)
                        report['layered'] = bool(style & 0x80000)
                        if not all(report[k] for k in ('click_through', 'no_activate', 'layered')):
                            raise RuntimeError('Native overlay styles are incomplete')
                        from ctypes import wintypes
                        user32 = ctypes.windll.user32
                        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)]
                        user32.GetWindowRect.restype = ctypes.c_int
                        user32.WindowFromPoint.argtypes = [wintypes.POINT]
                        user32.WindowFromPoint.restype = ctypes.c_void_p
                        rectangle = wintypes.RECT()
                        overlay_id = int(editor.overlay.winId())
                        if not user32.GetWindowRect(overlay_id, ctypes.byref(rectangle)):
                            raise RuntimeError('Could not inspect native overlay rectangle')
                        point = wintypes.POINT((rectangle.left + rectangle.right) // 2,
                                              (rectangle.top + rectangle.bottom) // 2)
                        underlying = user32.WindowFromPoint(point)
                        report['point_passes_through'] = bool(underlying and underlying != overlay_id)
                        if not report['point_passes_through']:
                            raise RuntimeError('Overlay intercepted native window hit testing')
                    report['passed'] = True
                    code = 0
                except Exception as exc:
                    report.update(passed=False, error=str(exc)); code = 1
                try:
                    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
                except OSError:
                    code = 1
                finally:
                    try: editor.shutdown()
                    finally: app.exit(code)
            QTimer.singleShot(500, finish)
        return app.exec()
    finally:
        try:
            if editor is not None: editor.shutdown()
            if manager is not None: manager.close()
        finally:
            lock.unlock()


if __name__ == '__main__':
    raise SystemExit(main())
