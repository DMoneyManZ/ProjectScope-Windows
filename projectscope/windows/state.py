"""Validated Windows preferences and presets; no GUI or operating-system bindings."""
import copy
import json
import os
from pathlib import Path
import random
import tempfile
import time

from projectscope.profiles import load_profile, validate_profile
from projectscope.storage import preset_catalog, save_named_profile
from projectscope.windows.hotkeys import DEFAULT_BINDINGS, parse_binding


class State:
    def __init__(self, stock: Path, data: Path):
        self.stock, self.data = Path(stock), Path(data)
        self.personal = self.data / 'presets'
        self.personal.mkdir(parents=True, exist_ok=True)
        self.path = self.data / 'settings.json'
        self.on_change = lambda: None
        self.warning = ''
        self._invalid = False
        self._values = dict(profile=load_profile(self.stock / 'cs2-precision.json'),
                            visible=True, monitor=-1, offset_x=0, offset_y=0,
                            hotkeys=dict(DEFAULT_BINDINGS))
        if self.path.exists():
            try:
                if self.path.stat().st_size > 262144:
                    raise ValueError('Preferences exceed the size limit')
                with self.path.open(encoding='utf-8') as handle:
                    loaded = json.load(handle)
                self._values = self._validate(loaded)
            except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
                self.warning = 'Saved preferences could not be loaded; defaults are shown. Original data will be backed up before saving.'
                self._invalid = True

    @property
    def profile(self): return copy.deepcopy(self._values['profile'])
    @property
    def hotkeys(self): return dict(self._values['hotkeys'])
    @property
    def visible(self): return self._values['visible']
    @property
    def monitor(self): return self._values['monitor']
    @property
    def offset_x(self): return self._values['offset_x']
    @property
    def offset_y(self): return self._values['offset_y']

    @staticmethod
    def _validate(values):
        if type(values) is not dict or set(values) != {'profile', 'visible', 'monitor', 'offset_x', 'offset_y', 'hotkeys'}:
            raise ValueError('Invalid preference fields')
        result = copy.deepcopy(values)
        result['profile'] = validate_profile(values['profile'])
        if type(values['visible']) is not bool: raise ValueError('Visibility must be a boolean')
        for key, low, high in [('monitor', -1, 63), ('offset_x', -32768, 32768), ('offset_y', -32768, 32768)]:
            if type(values[key]) is not int or not low <= values[key] <= high:
                raise ValueError(f'{key} must be an integer between {low} and {high}')
        mapping = values['hotkeys']
        if type(mapping) is not dict or set(mapping) != set(DEFAULT_BINDINGS):
            raise ValueError('Invalid shortcut actions')
        seen = set()
        for binding in mapping.values():
            if type(binding) is not str or len(binding) > 80:
                raise ValueError('Invalid shortcut text')
            parsed = parse_binding(binding)
            if parsed is not None:
                if parsed in seen: raise ValueError('Two actions cannot use the same shortcut')
                seen.add(parsed)
        return result

    def _commit(self, values):
        values = self._validate(values)
        payload = (json.dumps(values, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
        if self._invalid and self.path.exists():
            # Preserve the entire original file before replacing malformed settings.
            backup = self.data / f'settings.invalid-{time.time_ns()}.json'
            with backup.open('xb') as handle, self.path.open('rb') as source:
                while chunk := source.read(65536): handle.write(chunk)
                handle.flush(); os.fsync(handle.fileno())
            self._invalid = False
        fd, temporary = tempfile.mkstemp(prefix='.settings-', dir=self.data)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
        self._values = values
        self.on_change()

    def update_profile(self, profile):
        values = copy.deepcopy(self._values)
        values['profile'] = profile
        self._commit(values)

    def set_option(self, name, value):
        if name not in ('visible', 'monitor', 'offset_x', 'offset_y'):
            raise ValueError('Unknown setting')
        values = copy.deepcopy(self._values); values[name] = value
        self._commit(values)

    def set_hotkey(self, action, binding):
        if action not in DEFAULT_BINDINGS: raise ValueError('Unknown shortcut action')
        mapping = self.hotkeys; mapping[action] = binding
        self.set_hotkeys(mapping)

    def set_hotkeys(self, mapping):
        values = copy.deepcopy(self._values); values['hotkeys'] = mapping
        self._commit(values)

    def catalog(self): return preset_catalog(self.stock, self.personal)

    def cycle(self, direction):
        if direction not in (-1, 1): raise ValueError('Direction must be -1 or 1')
        entries = self.catalog()
        if not entries: return
        ids = [profile['id'] for _, profile in entries]
        try: index = ids.index(self.profile['id'])
        except ValueError: index = -1 if direction > 0 else 0
        self.update_profile(entries[(index + direction) % len(entries)][1])

    def save_preset(self, name):
        candidate = self.profile; candidate['name'] = name.strip()
        candidate = save_named_profile(candidate, self.personal)
        self.update_profile(candidate)
        return candidate

    def resize(self, direction):
        if direction not in (-1, 1): raise ValueError('Direction must be -1 or 1')
        profile = self.profile
        profile['style']['scale'] = round(max(.25, min(8, profile['style']['scale'] + direction * .25)), 6)
        self.update_profile(profile)

    def thicken(self, direction):
        if direction not in (-1, 1): raise ValueError('Direction must be -1 or 1')
        profile = self.profile
        for group in ('lines', 'dot', 'circle'):
            part = profile['style'][group]
            if part['enabled']:
                field = 'radius' if group == 'dot' else 'thickness'
                part[field] = round(max(.5, min(20, part[field] + direction * .25)), 6)
        self.update_profile(profile)

    def randomize(self):
        profile = self.profile; style = profile['style']
        family = random.choice(('lines', 'dot', 'circle'))
        for part in ('lines', 'dot', 'circle'): style[part]['enabled'] = part == family
        style['lines'].update(length=random.randint(3, 10), thickness=random.choice((1, 1.5, 2)), gap=random.randint(2, 5), top=True)
        style['dot']['radius'] = random.choice((1, 1.5, 2, 2.5))
        style['circle'].update(radius=random.randint(3, 8), thickness=random.choice((1, 1.5, 2)))
        style.update(scale=1, rotation=0, outline_width=1)
        profile.update(id='random-' + str(time.time_ns()), name='Random ' + family, description='Random compact design', game='General FPS')
        self.update_profile(profile)

    def cycle_color(self):
        palette = ['#FFFFFF', '#202020', '#00FFFF', '#003333', '#FFFF00', '#333300',
                   '#FF80FF', '#330033', '#80FF80', '#003300', '#FFB366', '#331900']
        profile = self.profile; style = profile['style']
        try: index = palette.index(style['color'].upper())
        except ValueError: index = -1
        index = (index + 1) % len(palette)
        style['color'] = palette[index]
        style['outline_color'] = '#000000' if index % 2 == 0 else '#FFFFFF'
        self.update_profile(profile)
