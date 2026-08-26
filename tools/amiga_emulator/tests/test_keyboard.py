from __future__ import annotations

import unittest

from amiga_emulator import keyboard
from amiga_emulator.keyboard import (
    BY_NAME,
    CHAR_KEYS,
    Keyboard,
    LSHIFT,
    RAMIGA,
    RAWKEYS,
    UnknownKeyError,
    plan_text,
    resolve,
)


def make_recording_keyboard() -> tuple[Keyboard, list[str]]:
    events: list[str] = []

    def fake_sender(command: str, *args: str) -> str:
        if command == "SEND_KEY":
            events.append(f"{args[0]}:{args[1]}")
        return ""

    return Keyboard(sender=fake_sender, delay=0), events


class RawKeyTableTests(unittest.TestCase):
    def test_letters_use_correct_codes(self) -> None:
        # Regression guards: Z was once mistyped as $30 and X/C/V drifted.
        expected = {
            "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14,
            "y": 0x15, "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19,
            "a": 0x20, "s": 0x21, "d": 0x22, "f": 0x23, "g": 0x24,
            "h": 0x25, "j": 0x26, "k": 0x27, "l": 0x28,
            "z": 0x31, "x": 0x32, "c": 0x33, "v": 0x34, "b": 0x35,
            "n": 0x36, "m": 0x37,
        }
        for name, code in expected.items():
            self.assertEqual(BY_NAME[name], code, name)
            self.assertEqual(RAWKEYS[code].unshifted, name)

    def test_modifier_and_special_keys(self) -> None:
        self.assertEqual(BY_NAME["lshift"], 0x60)
        self.assertEqual(BY_NAME["rshift"], 0x61)
        self.assertEqual(BY_NAME["lamiga"], 0x66)
        self.assertEqual(BY_NAME["ramiga"], 0x67)
        self.assertEqual(BY_NAME["return"], 0x44)
        self.assertEqual(BY_NAME["space"], 0x40)
        self.assertEqual(BY_NAME["f1"], 0x50)
        self.assertEqual(BY_NAME["f10"], 0x59)
        self.assertEqual(BY_NAME["help"], 0x5F)

    def test_all_printable_ascii_is_typeable(self) -> None:
        untypeable = {"\\", "|"}  # international keys only ($0D/$2B); no USA0 mapping
        for ordinal in range(0x20, 0x7F):
            char = chr(ordinal)
            if char in untypeable:
                self.assertNotIn(char, CHAR_KEYS)
                continue
            self.assertIn(char, CHAR_KEYS, f"untypeable: {char!r}")

    def test_shifted_chars_carry_shift_modifier(self) -> None:
        code, mods = CHAR_KEYS[":"]
        self.assertEqual(code, BY_NAME["semicolon"])
        self.assertEqual(mods, frozenset([LSHIFT]))
        code, mods = CHAR_KEYS[";"]
        self.assertEqual(mods, frozenset())

    def test_resolve_accepts_names_codes_and_characters(self) -> None:
        self.assertEqual(resolve("ramiga"), RAMIGA)
        self.assertEqual(resolve(0x67), RAMIGA)
        self.assertEqual(resolve(":"), 0x29)
        with self.assertRaises(UnknownKeyError):
            resolve("nosuchkey")
        with self.assertRaises(UnknownKeyError):
            resolve("\t")  # control chars are not typeable text

    def test_plan_text_groups_runs_by_modifiers(self) -> None:
        planned = plan_text("ab:cd")
        # a b share no modifiers; : needs shift; c d return to none.
        self.assertEqual(
            [(kind, len(mods), len(codes)) for kind, mods, codes in planned],
            [("keys", 0, 2), ("keys", 1, 1), ("keys", 0, 2)],
        )
        self.assertEqual(planned[1][2], [BY_NAME["semicolon"]])

    def test_plan_text_multi_modifier_chords(self) -> None:
        # explicit multi-modifier form, even where a shortcut exists
        planned = plan_text("{ctrl+shift+a}")
        self.assertEqual(
            planned,
            [("keys", frozenset([BY_NAME["ctrl"], LSHIFT]), [0x20])])
        planned = plan_text("{lshift+alt+amiga+x}")
        self.assertEqual(
            planned,
            [("keys",
              frozenset([LSHIFT, BY_NAME["lalt"], BY_NAME["lamiga"]]),
              [BY_NAME["x"]])])

    def test_plan_text_chord_tokens(self) -> None:
        planned = plan_text("{ramiga+e}")
        self.assertEqual(planned, [("keys", frozenset([RAMIGA]), [0x12])])
        # multi-modifier, char key part, and no merge into letter runs
        planned = plan_text("a{shift+;}b")
        self.assertEqual(len(planned), 3)
        self.assertEqual(planned[1], ("keys", frozenset([LSHIFT]), [0x29]))
        with self.assertRaises(UnknownKeyError):
            plan_text("{bogus+e}")     # not a modifier
        with self.assertRaises(UnknownKeyError):
            plan_text("{ramiga+nosuchkey}")
        with self.assertRaises(UnknownKeyError):
            plan_text("{+e}")

    def test_plan_text_supports_named_tokens(self) -> None:
        planned = plan_text("dir{return}")
        self.assertEqual(planned[-1], ("keys", frozenset(), [BY_NAME["return"]]))
        with self.assertRaises(UnknownKeyError):
            plan_text("{nosuch}")

    def test_plan_text_delay_token(self) -> None:
        planned = plan_text("dir{return}{delay:2.5}echo done{return}")
        kinds = [entry[0] for entry in planned]
        self.assertEqual(kinds.count("delay"), 1)
        self.assertIn(("delay", 2.5), planned)
        # delay splits the unshifted runs: no merge across the pause
        self.assertEqual(kinds, ["keys", "keys", "delay", "keys", "keys"])
        with self.assertRaises(UnknownKeyError):
            plan_text("{delay}")          # missing seconds
        with self.assertRaises(UnknownKeyError):
            plan_text("{delay:0}")        # must be positive
        with self.assertRaises(UnknownKeyError):
            plan_text("{delay:99}")       # capped at 60
        with self.assertRaises(UnknownKeyError):
            plan_text("{delay:abc}")      # not a number


class KeyboardEventTests(unittest.TestCase):
    def test_chord_holds_modifier_across_tap(self) -> None:
        kb, events = make_recording_keyboard()
        kb.prekey_amiga("e")
        ramiga_down, e_down, e_up, ramiga_up = events
        self.assertEqual((ramiga_down, e_down, e_up, ramiga_up),
                         (f"{RAMIGA}:1", "18:1", "18:0", f"{RAMIGA}:0"))

    def test_type_text_chord_token_holds_and_releases(self) -> None:
        kb, events = make_recording_keyboard()
        kb.type_text("{ramiga+e}")
        self.assertEqual(events, ["103:1", "18:1", "18:0", "103:0"])

    def test_type_text_multi_modifier_chord_order(self) -> None:
        kb, events = make_recording_keyboard()
        kb.type_text("{ctrl+shift+a}")
        # holds ascend, taps, releases descend; nothing after the chord
        self.assertEqual(events, ["96:1", "99:1", "32:1", "32:0", "99:0", "96:0"])

    def test_type_text_releases_before_unshifted_run(self) -> None:
        kb, events = make_recording_keyboard()
        kb.type_text(":a")
        # shift (from ':') must be released before the next unmodified tap
        self.assertLess(events.index("96:0"), events.index("32:1"))

    def test_type_text_token_and_screenshot_passthrough(self) -> None:
        kb, events = make_recording_keyboard()
        shots: list[tuple[str, ...]] = []

        def shot_sender(command: str, *args: str) -> str:
            if command == "SCREENSHOT":
                shots.append(args)
                return ""
            events.append(f"{args[0]}:{args[1]}")
            return ""

        kb2 = Keyboard(sender=shot_sender, delay=0)
        kb2.screenshot("/tmp/x.png", settle=0)
        kb2.type_text("hi{space}y")
        self.assertEqual(shots, [("/tmp/x.png",)])
        space_events = [e for e in events if e.startswith("64:")]
        self.assertEqual(len(space_events), 2)  # down + up

    def test_type_text_delay_sleeps_without_keystrokes(self) -> None:
        kb, events = make_recording_keyboard()
        sleeps: list[float] = []
        original_sleep = keyboard.time.sleep
        keyboard.time.sleep = lambda seconds: sleeps.append(seconds)
        try:
            kb.type_text("a{delay:1.5}b")
        finally:
            keyboard.time.sleep = original_sleep
        self.assertIn(1.5, sleeps)
        # exactly one down+up pair per character, none during the delay
        self.assertEqual(events, ["32:1", "32:0", "53:1", "53:0"])


    def test_release_all_sends_up_for_every_modifier(self) -> None:
        kb, events = make_recording_keyboard()
        kb.release_all()
        self.assertEqual(
            events,
            ["96:0", "97:0", "99:0", "100:0", "101:0", "102:0", "103:0"])


if __name__ == "__main__":
    unittest.main()
