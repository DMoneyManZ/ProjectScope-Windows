"""Portable, deliberately bounded shortcut syntax for RegisterHotKey.

Only named navigation keys, ASCII letters/digits and F1–F24 (except the
debugger-reserved F12) are supported. Layout-dependent punctuation and
multi-stroke sequences cannot be represented reliably as a global hotkey.
"""

DEFAULT_BINDINGS = {
    'toggle': 'Home',
    'previous': 'PageUp',
    'next': 'PageDown',
    'random': 'Pause',
    'save': 'Insert',
    'color': 'End',
    'size_up': 'Shift+PageUp',
    'size_down': 'Shift+PageDown',
    'thickness_up': 'Ctrl+PageUp',
    'thickness_down': 'Ctrl+PageDown',
}

_MODIFIERS = {'alt': 1, 'ctrl': 2, 'control': 2, 'shift': 4,
              'meta': 8, 'win': 8, 'windows': 8}
_KEYS = {
    'backspace': 0x08, 'tab': 0x09, 'return': 0x0D, 'enter': 0x0D,
    'pause': 0x13, 'escape': 0x1B, 'esc': 0x1B, 'space': 0x20,
    'pageup': 0x21, 'pgup': 0x21, 'pagedown': 0x22, 'pgdown': 0x22,
    'pgdn': 0x22, 'end': 0x23, 'home': 0x24, 'left': 0x25,
    'up': 0x26, 'right': 0x27, 'down': 0x28, 'insert': 0x2D,
    'ins': 0x2D, 'delete': 0x2E, 'del': 0x2E,
}


def parse_binding(text: str) -> tuple[int, int] | None:
    """Return Win32 modifiers/key, None for disabled, or raise ValueError.

    Accept Qt QKeySequence PortableText modifier/key names and familiar
    aliases, case-insensitively. MOD_NOREPEAT is added only at registration.
    """
    if not isinstance(text, str):
        raise ValueError('Shortcut must be text.')
    text = text.strip()
    if not text:
        return None
    if ',' in text:
        raise ValueError('Global shortcuts must contain a single key combination.')
    parts = [part.strip().lower() for part in text.split('+')]
    modifiers = 0
    for part in parts[:-1]:
        flag = _MODIFIERS.get(part)
        if flag is None:
            raise ValueError(f'Unsupported shortcut modifier: {part or "(empty)"}.')
        if modifiers & flag:
            raise ValueError(f'Duplicate shortcut modifier: {part}.')
        modifiers |= flag
    key = parts[-1]
    if key == 'f12':
        raise ValueError('F12 is reserved for the Windows debugger.')
    virtual_key = _KEYS.get(key)
    if len(key) == 1 and ('a' <= key <= 'z' or '0' <= key <= '9'):
        virtual_key = ord(key.upper())
    elif key.startswith('f') and key[1:].isascii() and key[1:].isdigit():
        number = int(key[1:])
        if 1 <= number <= 24 and key == f'f{number}':
            virtual_key = 0x6F + number
    if virtual_key is None:
        raise ValueError(f'Unsupported shortcut key: {key or "(empty)"}.')
    return modifiers, virtual_key
