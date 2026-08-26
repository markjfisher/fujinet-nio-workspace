"""Amiga raw-keyboard model and typing helpers for Amiberry IPC.

Raw-key codes follow the AmigaOS Keymap Library "ROM Default (USA0)"
console mapping (https://wiki.amigaos.net/wiki/Keymap_Library). Codes are
the classic raw key numbers ($00-$7F); Amiberry's ``SEND_KEY`` IPC command
takes them as decimal strings with state ``"1"`` (down) / ``"0"`` (up).

Every printable character knows its own key and modifier set, so callers
never hand-roll ``if ch == ':'`` logic::

    kb = Keyboard("/run/user/1000/amiberry.sock")
    kb.type_text("nio:bwcn.amiga")       # ':' chords Shift automatically
    kb.chord(["ramiga"], RAWKEYS[0x12])  # Amiga+E -> Workbench Execute

Modifier chords must be held across the tapped key: down, tap, release.
Releasing first yields the unmodified key (verified live: tap-method ';',
hold-method ':').
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from . import ipc


class UnknownKeyError(KeyError):
    """Raised when a character or key name has no raw-key mapping."""


@dataclass(frozen=True)
class Key:
    """One physical raw key and its default (USA) console mapping."""

    code: int  # raw key number, $00-$7F
    name: str  # stable identifier, e.g. "return", "z", "f1"
    unshifted: str | None = None  # produced alone (None = no output)
    shifted: str | None = None  # produced with Shift


def _k(code: int, name: str, unshifted: str | None = None,
       shifted: str | None = None) -> tuple[int, Key]:
    return code, Key(code, name, unshifted, shifted)


# ROM Default (USA0) console mapping. Printable low-map keys.
_LOW = [
    _k(0x00, "backquote", "`", "~"),
    _k(0x01, "1", "1", "!"),
    _k(0x02, "2", "2", "@"),
    _k(0x03, "3", "3", "#"),
    _k(0x04, "4", "4", "$"),
    _k(0x05, "5", "5", "%"),
    _k(0x06, "6", "6", "^"),
    _k(0x07, "7", "7", "&"),
    _k(0x08, "8", "8", "*"),
    _k(0x09, "9", "9", "("),
    _k(0x0A, "0", "0", ")"),
    _k(0x0B, "minus", "-", "_"),
    _k(0x0C, "equal", "=", "+"),
    # $0D is the international "|" key, absent from US keyboards.
    _k(0x10, "q", "q", "Q"),
    _k(0x11, "w", "w", "W"),
    _k(0x12, "e", "e", "E"),
    _k(0x13, "r", "r", "R"),
    _k(0x14, "t", "t", "T"),
    _k(0x15, "y", "y", "Y"),
    _k(0x16, "u", "u", "U"),
    _k(0x17, "i", "i", "I"),
    _k(0x18, "o", "o", "O"),
    _k(0x19, "p", "p", "P"),
    _k(0x1A, "bracket_left", "[", "{"),
    _k(0x1B, "bracket_right", "]", "}"),
    _k(0x20, "a", "a", "A"),
    _k(0x21, "s", "s", "S"),
    _k(0x22, "d", "d", "D"),
    _k(0x23, "f", "f", "F"),
    _k(0x24, "g", "g", "G"),
    _k(0x25, "h", "h", "H"),
    _k(0x26, "j", "j", "J"),
    _k(0x27, "k", "k", "K"),
    _k(0x28, "l", "l", "L"),
    _k(0x29, "semicolon", ";", ":"),
    _k(0x2A, "quote", "'", '"'),
    # $2B is the international "\" key, absent from US keyboards.
    _k(0x31, "z", "z", "Z"),  # NOT $30 — see workspace history
    _k(0x32, "x", "x", "X"),
    _k(0x33, "c", "c", "C"),
    _k(0x34, "v", "v", "V"),
    _k(0x35, "b", "b", "B"),
    _k(0x36, "n", "n", "N"),
    _k(0x37, "m", "m", "M"),
    _k(0x38, "comma", ",", "<"),
    _k(0x39, "period", ".", ">"),
    _k(0x3A, "slash", "/", "?"),
]

# High-map keys ($40+) and modifier keys.
_HIGH = [
    _k(0x40, "space", " "),
    _k(0x41, "backspace"),
    _k(0x42, "tab"),
    _k(0x43, "enter"),  # numeric-pad Enter
    _k(0x44, "return"),
    _k(0x45, "escape"),
    _k(0x46, "delete"),
    _k(0x4C, "up"),
    _k(0x4D, "down"),
    _k(0x4E, "right"),
    _k(0x4F, "left"),
    *(_k(0x50 + i, f"f{i + 1}") for i in range(10)),
    _k(0x5F, "help"),
    _k(0x60, "lshift"),
    _k(0x61, "rshift"),
    _k(0x62, "capslock"),
    _k(0x63, "ctrl"),
    _k(0x64, "lalt"),
    _k(0x65, "ralt"),
    _k(0x66, "lamiga"),
    _k(0x67, "ramiga"),
]

RAWKEYS: dict[int, Key] = dict(_LOW + _HIGH)
BY_NAME: dict[str, int] = {key.name: key.code for key in RAWKEYS.values()}

LSHIFT = BY_NAME["lshift"]
RSHIFT = BY_NAME["rshift"]
LAMIGA = BY_NAME["lamiga"]
RAMIGA = BY_NAME["ramiga"]
RETURN = BY_NAME["return"]
SPACE = BY_NAME["space"]

# Character -> (raw key code, required modifier codes).
CHAR_KEYS: dict[str, tuple[int, frozenset[int]]] = {}
for _key in RAWKEYS.values():
    if _key.unshifted is not None and _key.unshifted not in CHAR_KEYS:
        CHAR_KEYS[_key.unshifted] = (_key.code, frozenset())
    if _key.shifted is not None and _key.shifted not in CHAR_KEYS:
        CHAR_KEYS[_key.shifted] = (_key.code, frozenset([LSHIFT]))

_TOKEN_RE = re.compile(r"\{([a-z0-9]+)(?::([^}]*))?\}")


def resolve(key: str | int) -> int:
    """Accept a raw code, key name, or single character; return a code."""
    if isinstance(key, int):
        if key not in RAWKEYS:
            raise UnknownKeyError(f"no such raw key: {key:#04x}")
        return key
    if len(key) == 1:
        try:
            return CHAR_KEYS[key][0]
        except KeyError:
            raise UnknownKeyError(f"no mapping for character {key!r}") from None
    name = key.lower()
    if name in BY_NAME:
        return BY_NAME[name]
    raise UnknownKeyError(f"no such key name: {key!r}")


def char_sequence(char: str) -> tuple[int, frozenset[int]]:
    """Map one character to (raw key code, required modifier codes)."""
    try:
        return CHAR_KEYS[char]
    except KeyError:
        raise UnknownKeyError(
            f"no mapping for character {char!r}; "
            "use {{name}} tokens for special keys") from None


def plan_text(text: str) -> list[tuple]:
    """Group ``text`` into a plan of ``("keys", mods, codes)`` / ``("delay", seconds)``.

    Consecutive taps sharing one modifier set merge into one hold. Named
    keys are tokens: ``"{esc}dir {return}"``. ``{delay:seconds}`` is a
    pause before the next keystroke (guests drop keys while busy).
    """
    planned: list[tuple] = []
    position = 0
    while position < len(text):
        token = _TOKEN_RE.match(text, position)
        if token:
            name, argument = token.group(1), token.group(2)
            position = token.end()
            if name == "delay":
                if argument is None:
                    raise UnknownKeyError("{delay} requires seconds: {delay:2.5}")
                try:
                    seconds = float(argument)
                except ValueError:
                    raise UnknownKeyError(
                        f"{{delay}} seconds not a number: {argument!r}") from None
                if not 0.0 < seconds <= 60.0:
                    raise UnknownKeyError(
                        f"{{delay}} out of range (0,60]: {argument}")
                planned.append(("delay", seconds))
                continue
            if argument is not None:
                raise UnknownKeyError(
                    f"{{{name}}} takes no argument; did you mean {{delay:{argument}}}?")
            if name not in BY_NAME:
                raise UnknownKeyError(f"no such key name: {{{name}}}")
            planned.append(("keys", frozenset(), [BY_NAME[name]]))
            continue  # tokens never merge into letter runs
        code, mods = char_sequence(text[position])
        position += 1
        if planned and planned[-1][0] == "keys" and planned[-1][1] == mods:
            planned[-1][2].append(code)
        else:
            planned.append(("keys", mods, [code]))
    return planned


Sender = Callable[..., str]


class Keyboard:
    """Send raw-key events to one Amiberry instance over its IPC socket."""

    def __init__(self, socket: str | Path | None = None,
                 delay: float = 0.03, sender: Sender | None = None) -> None:
        self._socket = Path(socket) if socket else None
        self._delay = delay
        self._send_request = sender if sender is not None \
            else (lambda command, *args:
                  ipc.request(self._ensure_socket(), command, *args))

    def _ensure_socket(self) -> Path:
        if self._socket is None:
            self._socket = ipc.find_socket()
        return self._socket

    # -- primitives ----------------------------------------------------

    def send(self, code: int, state: str, delay: float | None = None) -> None:
        """One SEND_KEY event: state "1" = down, "0" = up."""
        self._send_request("SEND_KEY", str(resolve(code)), state)
        time.sleep(self._delay if delay is None else delay)

    def press(self, code: int, delay: float | None = None) -> None:
        self.send(code, "1", delay)

    def release(self, code: int, delay: float | None = None) -> None:
        self.send(code, "0", delay)

    def tap(self, code: int, delay: float | None = None) -> None:
        self.press(code, delay)
        self.release(code, delay)

    def chord(self, modifiers: Iterable[str | int],
              code: str | int, delay: float | None = None) -> None:
        """Hold every modifier while tapping ``code``, then release them."""
        held = [resolve(m) for m in modifiers]
        target = resolve(code)
        for mod in held:
            self.press(mod, delay)
        self.tap(target, delay)
        for mod in reversed(held):
            self.release(mod, delay)

    # -- convenience chords ---------------------------------------------

    def prekey_amiga(self, key: str | int, delay: float | None = None) -> None:
        """Amiga+``key`` chord, e.g. ``prekey_amiga("e")`` -> Execute dialog."""
        self.chord([RAMIGA], key, delay)

    def prekey_shift(self, key: str | int, delay: float | None = None) -> None:
        self.chord([LSHIFT], key, delay)

    # -- text ------------------------------------------------------------

    def type_text(self, text: str, delay: float | None = None) -> None:
        """Type characters, resolving each one's own modifiers.

        Consecutive characters needing the same modifiers share one hold.
        Special keys use ``{name}`` tokens: ``"dir{return}"``,
        ``"{esc}q"``, ``"save {f1}"``. ``{delay:seconds}`` pauses before
        the next keystroke — use it after ``{return}`` while the guest is
        busy: ``"dir{return}{delay:2.5}echo done{return}"``.
        """
        for entry in plan_text(text):
            if entry[0] == "delay":
                time.sleep(entry[1])
                continue
            _, mods, codes = entry
            for mod in sorted(mods):
                self.press(mod, delay)
            for code in codes:
                self.tap(code, delay)
            for mod in sorted(mods, reverse=True):
                self.release(mod, delay)

    def screenshot(self, path: str | Path, settle: float = 1.0) -> None:
        time.sleep(settle)
        self._send_request("SCREENSHOT", str(path))
        time.sleep(0.5)


__all__ = [
    "Keyboard", "Key", "UnknownKeyError",
    "RAWKEYS", "BY_NAME", "CHAR_KEYS",
    "resolve", "char_sequence", "plan_text",
    "LSHIFT", "RSHIFT", "LAMIGA", "RAMIGA", "RETURN", "SPACE",
]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: type ``text`` into the live Amiberry instance.

    >>> scripts/amiberry-type 'dir NIO:{return}{delay:2.5}echo done{return}'
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="amiberry-type",
        description="Type text into the live Amiberry instance over IPC. "
                    "Characters resolve their own Shift chords; special keys "
                    "use {name} tokens ({return}, {esc}, {space}, {f1}...); "
                    "{delay:seconds} pauses between keystrokes.")
    parser.add_argument("--socket", dest="socket_path",
                        help="Amiberry IPC socket (default: autodetect)")
    parser.add_argument("--delay", type=float, default=0.01,
                        help="per-event hold delay in seconds (default 0.01)")
    parser.add_argument("--screenshot", metavar="PATH",
                        help="capture a screenshot after typing")
    parser.add_argument("--settle", type=float, default=1.0,
                        help="seconds to wait before --screenshot (default 1.0)")
    parser.add_argument("text", help="text to type, with {token} specials")
    args = parser.parse_args(argv)

    keyboard = Keyboard(socket=args.socket_path, delay=args.delay)
    keyboard.type_text(args.text)
    if args.screenshot:
        keyboard.screenshot(args.screenshot, settle=args.settle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
