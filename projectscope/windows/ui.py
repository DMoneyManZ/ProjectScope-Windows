"""ProjectScope Windows studio, preview, click-through overlay, and tray."""
import copy
import math
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QSplitter, QSystemTrayIcon,
    QTabWidget, QVBoxLayout, QWidget,
)
from projectscope.profiles import load_profile, save_profile
from projectscope.render import extent
from .painting import render_image

STYLE = '''
QWidget { background: #171b20; color: #edf0f2; font-family: "Segoe UI", "DejaVu Sans"; font-size: 13px; }
QMainWindow, QDialog { background: #171b20; }
QLabel#brand { font-size: 25px; font-weight: 700; }
QLabel#title { font-size: 23px; font-weight: 600; }
QLabel#muted { color: #a1aeb8; }
QLabel#status { color: #93ddc0; padding: 7px 0; }
QPushButton { background: #252e37; border: 1px solid #3d4a55; border-radius: 5px; padding: 8px 13px; }
QPushButton:hover { background: #34434a; border-color: #93ddc0; }
QPushButton:focus, QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #93ddc0; }
QPushButton#primary { background: #93ddc0; color: #172720; border: 0; font-weight: 600; }
QPushButton#primary:hover { background: #b2ebd5; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox { background: #202831; border: 1px solid #3d4a55; border-radius: 4px; padding: 6px; min-height: 20px; }
QComboBox QAbstractItemView { background: #202831; selection-background-color: #37594f; }
QListWidget { background: #1c232b; border: 0; outline: 0; }
QListWidget::item { padding: 9px 6px; border-bottom: 1px solid #29333e; }
QListWidget::item:selected { background: #2d4942; color: #d5ffee; }
QListWidget::item:hover { background: #283940; }
QCheckBox { spacing: 9px; padding: 4px 0; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #697985; border-radius: 3px; background: #202831; }
QCheckBox::indicator:checked { background: #93ddc0; border-color: #93ddc0; image: none; }
QTabWidget::pane { border: 0; padding-top: 12px; }
QTabBar::tab { padding: 10px 14px; border-bottom: 2px solid #34414c; color: #a1aeb8; }
QTabBar::tab:selected { color: #93ddc0; border-bottom: 2px solid #93ddc0; }
QScrollArea { border: 0; }
QScrollBar:vertical { width: 10px; background: #171b20; }
QScrollBar::handle:vertical { background: #465762; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMenu { background: #202831; border: 1px solid #465762; padding: 5px; }
QMenu::item { padding: 7px 22px; }
QMenu::item:selected { background: #37594f; }
QToolTip { background: #263b35; color: #edf0f2; border: 1px solid #93ddc0; }
'''


def label(text, kind=None):
    item = QLabel(text)
    if kind:
        item.setObjectName(kind)
    return item


class Preview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.style = None
        self.setMinimumSize(280, 240)
        self.background = '#10171e'

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(self.background))
        painter.setPen(QPen(QColor('#23313c'), 1))
        cx, cy = self.width() / 2, self.height() / 2
        for x in range(int(cx) % 24, self.width(), 24):
            painter.drawLine(x, 0, x, self.height())
        for y in range(int(cy) % 24, self.height(), 24):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(QColor('#3c515d'), 1))
        painter.drawEllipse(QPointF(cx, cy), 78, 78)
        painter.drawEllipse(QPointF(cx, cy), 132, 132)
        painter.setPen(QColor('#a1aeb8'))
        painter.drawText(18, 27, 'Live preview')
        painter.drawText(18, self.height() - 17, '1:1 logical pixels')
        if self.style:
            image = render_image(self.style, device_pixel_ratio=self.devicePixelRatioF())
            painter.drawImage(QPointF(cx - image.deviceIndependentSize().width() / 2,
                                     cy - image.deviceIndependentSize().height() / 2), image)


class Overlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput |
                         Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.style = None
        self.setWindowTitle('ProjectScope overlay')

    def sync(self, state):
        self.style = copy.deepcopy(state.profile['style'])
        screens = QApplication.screens()
        screen = screens[state.monitor] if 0 <= state.monitor < len(screens) else QApplication.primaryScreen()
        if screen is None:
            self.hide()
            return
        area = screen.geometry()
        size = math.ceil(2 * extent(self.style))
        self.setGeometry(round(area.x() + area.width() / 2 + state.offset_x - size / 2),
                         round(area.y() + area.height() / 2 + state.offset_y - size / 2), size, size)
        self.setVisible(state.visible)
        self.update()

    def paintEvent(self, event):
        if self.style:
            painter = QPainter(self)
            painter.drawImage(QPointF(0, 0), render_image(self.style, self.width(), self.height(),
                                                       device_pixel_ratio=self.devicePixelRatioF()))


class Editor(QMainWindow):
    def __init__(self, state, root: Path, hotkeys=None):
        super().__init__()
        self.state, self.root = state, Path(root)
        self.hotkeys = None
        self._syncing = False
        self._closed = False
        self._catalog_ids = None
        self._registered = None
        self._hotkey_errors = {}
        self._action_error = ''
        self._screen_connections = []
        self.controls = {}
        self.overlay = Overlay()
        self.setWindowTitle('ProjectScope — Crosshair studio')
        self.resize(1170, 820)
        self.setMinimumSize(910, 680)
        self.setStyleSheet(STYLE)
        self.icon = QIcon(str(self.root / 'assets/projectscope.svg'))
        self.setWindowIcon(self.icon)
        self._build()
        self._setup_tray()
        self.state.on_change = self.sync
        app = QApplication.instance()
        app.screenAdded.connect(self._screens_changed)
        app.screenRemoved.connect(self._screens_changed)
        self._screens_changed()
        if hotkeys is not None:
            self.bind_hotkeys(hotkeys)
        self.sync()

    def _button(self, text, callback, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName('primary')
        button.clicked.connect(lambda: self._perform(callback))
        return button

    def _perform(self, callback):
        try:
            return callback()
        except (OSError, ValueError) as exc:
            self.sync()
            QMessageBox.warning(self, 'ProjectScope', str(exc))

    def _perform_background(self, action, callback):
        """Global shortcuts must never open a modal dialog or activate the editor."""
        self._action_error = ''
        try:
            return callback()
        except (OSError, ValueError) as exc:
            self._action_error = f'{action.replace("_", " ").capitalize()} failed: {exc}'
            self.sync()
            if self.tray_available:
                self.tray.showMessage('ProjectScope', self._action_error,
                                      QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(24, 20, 24, 14)
        outer.setSpacing(18)
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.icon.pixmap(42, 42))
        header.addWidget(icon)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(label('ProjectScope', 'brand'))
        brand.addWidget(label('Crosshair studio', 'muted'))
        header.addLayout(brand)
        header.addStretch()
        self.visible = QCheckBox('Overlay visible')
        self.visible.toggled.connect(lambda value: self._option('visible', value))
        header.addWidget(self.visible)
        header.addSpacing(12)
        header.addWidget(self._button('Save preset', self.save_preset, True))
        outer.addLayout(header)
        split = QSplitter(Qt.Orientation.Horizontal)
        sidebar = QWidget()
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 12, 0)
        side.addWidget(label('Preset library', 'title'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find a preset or game')
        self.search.textChanged.connect(self._filter)
        side.addWidget(self.search)
        self.preset_list = QListWidget()
        self.preset_list.setIconSize(QSize(34, 34))
        self.preset_list.currentItemChanged.connect(self._select_preset)
        side.addWidget(self.preset_list, 1)
        side_buttons = QHBoxLayout()
        side_buttons.addWidget(self._button('Import', self._import_dialog))
        side_buttons.addWidget(self._button('Export', self._export_dialog))
        side.addLayout(side_buttons)
        split.addWidget(sidebar)
        main = QWidget()
        middle = QVBoxLayout(main)
        middle.setContentsMargins(8, 0, 12, 0)
        self.title = label('', 'title')
        middle.addWidget(self.title)
        self.description = label('', 'muted')
        self.description.setWordWrap(True)
        self.description.setMinimumHeight(44)
        middle.addWidget(self.description)
        self.preview = Preview()
        middle.addWidget(self.preview, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self._button('Randomize', self.state.randomize))
        buttons.addWidget(self._button('Cycle color', self.state.cycle_color))
        middle.addLayout(buttons)
        self.placement = label('', 'muted')
        middle.addWidget(self.placement)
        split.addWidget(main)
        tabs = QTabWidget()
        tabs.setMinimumWidth(292)
        shape = QWidget()
        form = QFormLayout(shape)
        form.setContentsMargins(6, 6, 6, 6)
        form.setSpacing(11)
        for path, text in [('lines.enabled', 'Cross lines'), ('lines.top', 'Top arm')]:
            self._check(form, path, text)
        for path, text, low, high, step in [
            ('lines.length', 'Length', 1, 100, 1), ('lines.thickness', 'Thickness', .5, 20, .5),
            ('lines.gap', 'Center gap', 0, 100, 1)]:
            self._number(form, path, text, low, high, step)
        self._check(form, 'dot.enabled', 'Center dot')
        self._number(form, 'dot.radius', 'Dot radius', .5, 20, .5)
        self._check(form, 'circle.enabled', 'Circle')
        self._number(form, 'circle.radius', 'Circle radius', 1, 100, 1)
        self._number(form, 'circle.thickness', 'Circle width', .5, 20, .5)
        form.addRow(label('Appearance', 'title'))
        for path, text in [('color', 'Color'), ('outline_color', 'Outline color')]:
            button = self._button('', lambda p=path: self._pick_color(p))
            self.controls[path] = button
            form.addRow(text, button)
        self._number(form, 'outline_width', 'Outline width', 0, 8, .5)
        self._number(form, 'opacity', 'Opacity', 0, 1, .05)
        self._number(form, 'rotation', 'Rotation', -180, 180, 5)
        self.controls['rotation'].setSuffix('°')
        self._number(form, 'scale', 'Scale', .25, 8, .25)
        self.controls['scale'].setSuffix('×')
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(shape)
        tabs.addTab(scroll, 'Design')
        placement = QWidget()
        settings = QVBoxLayout(placement)
        settings.setContentsMargins(6, 10, 6, 6)
        settings.addWidget(label('Display & position', 'title'))
        settings.addWidget(label('Place the overlay at the display center.', 'muted'))
        position = QFormLayout()
        self.monitor = QComboBox()
        self.monitor.currentIndexChanged.connect(lambda index: self._option('monitor', self.monitor.itemData(index)))
        position.addRow('Display', self.monitor)
        for name, text in [('offset_x', 'Horizontal'), ('offset_y', 'Vertical')]:
            widget = QSpinBox()
            widget.setRange(-32768, 32768)
            widget.setSuffix(' px')
            widget.valueChanged.connect(lambda value, n=name: self._option(n, value))
            setattr(self, name, widget)
            position.addRow(text, widget)
        settings.addLayout(position)
        settings.addWidget(self._button('Center overlay', self._center))
        settings.addSpacing(18)
        settings.addWidget(label('Global shortcuts', 'title'))
        info = label('Use shortcuts while another application is focused. Conflicts appear below.', 'muted')
        info.setWordWrap(True)
        settings.addWidget(info)
        settings.addWidget(self._button('Customize shortcuts', self._shortcut_dialog))
        settings.addStretch()
        tabs.addTab(placement, 'Placement')
        split.addWidget(tabs)
        split.setSizes([248, 540, 310])
        split.setCollapsible(0, False)
        split.setCollapsible(1, False)
        split.setCollapsible(2, False)
        outer.addWidget(split, 1)
        footer = QHBoxLayout()
        self.status = label('', 'status')
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        footer.addWidget(self._button('Shortcuts', self._shortcut_dialog))
        footer.addWidget(self._button('Quit', self.quit))
        outer.addLayout(footer)

    def _check(self, form, path, text):
        widget = QCheckBox(text)
        widget.toggled.connect(lambda value: self._style_value(path, value))
        self.controls[path] = widget
        form.addRow(widget)

    def _number(self, form, path, text, low, high, step):
        widget = QDoubleSpinBox()
        widget.setRange(low, high)
        widget.setSingleStep(step)
        widget.setDecimals(2 if step < .5 else 1)
        widget.setKeyboardTracking(False)
        widget.valueChanged.connect(lambda value: self._style_value(path, value))
        self.controls[path] = widget
        form.addRow(text, widget)

    def _style_value(self, path, value):
        if self._syncing:
            return
        profile = copy.deepcopy(self.state.profile)
        target = profile['style']
        parts = path.split('.')
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
        self._perform(lambda: self.state.update_profile(profile))

    def _option(self, name, value):
        if not self._syncing:
            self._perform(lambda: self.state.set_option(name, value))

    def _pick_color(self, path):
        color = QColorDialog.getColor(QColor(self.state.profile['style'][path]), self, 'Choose crosshair color')
        if color.isValid():
            self._style_value(path, color.name())

    def _select_preset(self, item, previous):
        if item is not None and not self._syncing:
            self._perform(lambda: self.state.update_profile(item.data(Qt.ItemDataRole.UserRole)))

    def _filter(self, text):
        for index in range(self.preset_list.count()):
            item = self.preset_list.item(index)
            profile = item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(text.lower() not in (profile['name'] + ' ' + profile['game']).lower())

    def _screens_changed(self, *args):
        for screen in self._screen_connections:
            try:
                screen.geometryChanged.disconnect(self._screen_geometry_changed)
            except (RuntimeError, TypeError):
                pass
        self._screen_connections = list(QApplication.screens())
        for screen in self._screen_connections:
            screen.geometryChanged.connect(self._screen_geometry_changed)
        self._screen_geometry_changed()

    def _screen_geometry_changed(self, *args):
        self._syncing = True
        self.monitor.clear()
        self.monitor.addItem('Primary display', -1)
        for index, screen in enumerate(QApplication.screens()):
            rect = screen.geometry()
            self.monitor.addItem(f'{index + 1}: {screen.name()} ({rect.width()} × {rect.height()})', index)
        self._syncing = False
        self.sync()

    def sync(self):
        if self._closed:
            return
        self._syncing = True
        try:
            profile = self.state.profile
            self.title.setText(profile['name'])
            self.description.setText(profile['description'] or profile['game'])
            self.preview.style = copy.deepcopy(profile['style'])
            self.preview.update()
            for path, widget in self.controls.items():
                value = profile['style']
                for part in path.split('.'):
                    value = value[part]
                if isinstance(widget, QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(value)
                else:
                    widget.setText(value.upper())
                    widget.setStyleSheet(f'QPushButton {{ border-left: 14px solid {value}; }}')
            self.visible.setChecked(self.state.visible)
            self.offset_x.setValue(self.state.offset_x)
            self.offset_y.setValue(self.state.offset_y)
            self.monitor.setCurrentIndex(max(0, self.monitor.findData(self.state.monitor)))
            catalog = self.state.catalog()
            signature = [(str(path), repr(item)) for path, item in catalog]
            if signature != self._catalog_ids:
                self._catalog_ids = signature
                self.preset_list.clear()
                for _, item_profile in catalog:
                    item = QListWidgetItem(item_profile['name'])
                    item.setToolTip(item_profile['game'] + '\n' + item_profile['description'])
                    item.setData(Qt.ItemDataRole.UserRole, item_profile)
                    thumb = render_image(item_profile['style'], 42, 42)
                    item.setIcon(QIcon(QPixmap.fromImage(thumb)))
                    self.preset_list.addItem(item)
                self._filter(self.search.text())
            for index in range(self.preset_list.count()):
                if self.preset_list.item(index).data(Qt.ItemDataRole.UserRole)['id'] == profile['id']:
                    self.preset_list.setCurrentRow(index)
                    break
            else:
                self.preset_list.setCurrentRow(-1)
            self.overlay.sync(self.state)
            self.placement.setText(f"{self.monitor.currentText()}  •  X {self.state.offset_x:+d} / Y {self.state.offset_y:+d} px")
            if self.hotkeys is not None and self._registered != self.state.hotkeys:
                self._hotkey_errors = self.hotkeys.register(self.state.hotkeys)
                self._registered = dict(self.state.hotkeys)
            problems = [message for message in (self.state.warning, self._action_error) if message]
            problems.extend(f'{action}: {error}' for action, error in self._hotkey_errors.items())
            if problems:
                self.status.setText('  '.join(problems))
            else:
                self.status.setText('Close to tray; use Quit to exit.' if self.tray_available else 'Tray unavailable. Closing this window exits ProjectScope.')
            self.tray_toggle.setText('Hide overlay' if self.state.visible else 'Show overlay')
        finally:
            self._syncing = False

    def _center(self):
        self.state.set_option('offset_x', 0)
        self.state.set_option('offset_y', 0)

    def import_profile(self, path):
        self.state.update_profile(load_profile(path))

    def export_profile(self, path):
        save_profile(path, self.state.profile)

    def _import_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import preset', '', 'ProjectScope preset (*.json)')
        if path:
            self.import_profile(path)

    def _export_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export preset', self.state.profile['id'] + '.json', 'ProjectScope preset (*.json)')
        if path:
            self.export_profile(path)

    def save_preset(self):
        self.reopen()
        name, accepted = QInputDialog.getText(self, 'Save preset', 'Preset name', text=self.state.profile['name'])
        if accepted:
            self.state.save_preset(name.strip())

    def set_hotkey(self, action, binding):
        mapping = self.state.hotkeys
        if action not in mapping:
            raise ValueError('Unknown shortcut action')
        mapping[action] = binding
        self.set_hotkeys(mapping)

    def set_hotkeys(self, mapping):
        previous = self.state.hotkeys
        self.state.set_hotkeys(mapping)
        errors = dict(self._hotkey_errors)
        if errors:
            try:
                self.state.set_hotkeys(previous)
            except OSError as exc:
                raise OSError(f'Shortcut registration failed and previous settings could not be restored: {exc}') from exc
            active = getattr(self.hotkeys, 'active_bindings', {})
            expected = {action: binding.strip() for action, binding in previous.items() if binding.strip()}
            detail = ('Previous shortcuts retained.' if active == expected else
                      'Previous settings restored, but some shortcuts are unavailable; check the status message.')
            raise ValueError(' '.join(f'{action}: {error}' for action, error in errors.items()) + ' ' + detail)

    def _shortcut_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Global shortcuts')
        dialog.setMinimumWidth(460)
        layout = QVBoxLayout(dialog)
        info = label('Use Ctrl, Alt, Shift or Win with a key. Clear a binding to disable it.', 'muted')
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QFormLayout()
        fields = {}
        names = {'toggle': 'Show / hide overlay', 'previous': 'Previous preset', 'next': 'Next preset',
                 'random': 'Randomize', 'save': 'Save preset', 'color': 'Cycle color',
                 'size_up': 'Increase size', 'size_down': 'Decrease size',
                 'thickness_up': 'Increase thickness', 'thickness_down': 'Decrease thickness'}
        for action, binding in self.state.hotkeys.items():
            field = QLineEdit(binding)
            field.setPlaceholderText('Disabled')
            fields[action] = field
            form.addRow(names.get(action, action), field)
        layout.addLayout(form)
        feedback = label('', 'status')
        feedback.setWordWrap(True)
        layout.addWidget(feedback)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(dialog.reject)
        def apply():
            try:
                self.set_hotkeys({action: field.text().strip() for action, field in fields.items()})
                dialog.accept()
            except (OSError, ValueError) as exc:
                feedback.setText(str(exc))
        buttons.accepted.connect(apply)
        layout.addWidget(buttons)
        dialog.exec()

    def _setup_tray(self):
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip('ProjectScope')
        self.tray_menu = QMenu(self)
        self.tray_open = QAction('Open crosshair studio', self)
        self.tray_open.triggered.connect(self.reopen)
        self.tray_menu.addAction(self.tray_open)
        self.tray_toggle = QAction('Show overlay', self)
        self.tray_toggle.triggered.connect(lambda: self._perform(lambda: self.state.set_option('visible', not self.state.visible)))
        self.tray_menu.addAction(self.tray_toggle)
        self.tray_menu.addSeparator()
        self.tray_quit = QAction('Quit ProjectScope', self)
        self.tray_quit.triggered.connect(self.quit)
        self.tray_menu.addAction(self.tray_quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activated)
        if self.tray_available:
            self.tray.show()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.reopen()

    def reopen(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def bind_hotkeys(self, manager):
        if self.hotkeys is not None and self.hotkeys is not manager:
            self.hotkeys.close()
        self.hotkeys = manager
        self._registered = None
        self.sync()

    def hotkey_callbacks(self):
        actions = {
            'toggle': lambda: self.state.set_option('visible', not self.state.visible),
            'previous': lambda: self.state.cycle(-1), 'next': lambda: self.state.cycle(1),
            'random': self.state.randomize, 'save': lambda: self.state.save_preset(self.state.profile['name']),
            'color': self.state.cycle_color,
            'size_up': lambda: self.state.resize(1), 'size_down': lambda: self.state.resize(-1),
            'thickness_up': lambda: self.state.thicken(1), 'thickness_down': lambda: self.state.thicken(-1),
        }
        return {name: lambda action=name, callback=callback: self._perform_background(action, callback)
                for name, callback in actions.items()}

    def closeEvent(self, event):
        if self.tray_available and not self._closed:
            self.hide()
            event.ignore()
        else:
            self.shutdown()
            event.accept()
            QApplication.instance().quit()

    def quit(self):
        self.shutdown()
        QApplication.instance().quit()

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self.state.on_change = lambda: None
        self.tray.hide()
        self.overlay.hide()
        self.overlay.deleteLater()
        if self.hotkeys is not None:
            self.hotkeys.close()
        app = QApplication.instance()
        app.screenAdded.disconnect(self._screens_changed)
        app.screenRemoved.disconnect(self._screens_changed)
        for screen in self._screen_connections:
            try:
                screen.geometryChanged.disconnect(self._screen_geometry_changed)
            except (RuntimeError, TypeError):
                pass
        self.hide()
