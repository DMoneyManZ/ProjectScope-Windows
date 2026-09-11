import unittest

from projectscope.windows.hotkeys import DEFAULT_BINDINGS, parse_binding


class BindingParserTests(unittest.TestCase):
    def test_defaults_parse_to_unique_windows_key_combinations(self):
        bindings = [parse_binding(value) for value in DEFAULT_BINDINGS.values()]
        self.assertNotIn(None, bindings)
        self.assertEqual(len(bindings), len(set(bindings)))
        self.assertEqual(parse_binding(DEFAULT_BINDINGS['toggle']), (0, 0x24))
        self.assertEqual(parse_binding(DEFAULT_BINDINGS['size_up']), (4, 0x21))
        self.assertEqual(parse_binding(DEFAULT_BINDINGS['thickness_down']), (2, 0x22))

    def test_portable_text_and_aliases_map_to_windows_values(self):
        cases = {
            'Home': (0, 0x24), 'PageUp': (0, 0x21), 'PgDown': (0, 0x22),
            'Ins': (0, 0x2D), 'Del': (0, 0x2E), 'Pause': (0, 0x13),
            'End': (0, 0x23), 'Ctrl+Shift+F11': (6, 0x7A),
            ' Control + alt + a ': (3, 0x41), 'Meta+9': (8, 0x39),
            'Win+Left': (8, 0x25), 'Esc': (0, 0x1B), 'Space': (0, 0x20),
            'Backspace': (0, 8), 'Tab': (0, 9), 'Enter': (0, 13),
            'Return': (0, 13), 'F24': (0, 0x87), 'Shift+PgUp': (4, 0x21),
        }
        for binding, expected in cases.items():
            with self.subTest(binding=binding):
                self.assertEqual(parse_binding(binding), expected)

    def test_empty_binding_disables_a_key(self):
        self.assertIsNone(parse_binding(''))
        self.assertIsNone(parse_binding('  '))

    def test_invalid_bindings_raise_a_validation_error(self):
        for binding in ['Ctrl', 'Ctrl+Ctrl+A', 'Ctrl+Control+A',
                        'Ctrl+K, Ctrl+C', 'F12', 'Ctrl+F12', 'F0', 'F25',
                        'Hyper+A', 'Ctrl++', '+A', 'A+B', 'A+Ctrl',
                        'Num+1', 'é', '☃', 'Ctrl+Unknown', None, 42]:
            with self.subTest(binding=binding):
                with self.assertRaises(ValueError):
                    parse_binding(binding)


if __name__ == '__main__':
    unittest.main()
