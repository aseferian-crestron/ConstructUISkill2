"""Shared TOML basic-string writer, per the TOML spec's escape rules -- used by every
module that writes a `{...Attributes}` table (project.py, elements.py, page.py) so the
escaping logic exists in exactly one place.

Bug found 2026-09-03 (Phase 3 nested-element test): the original per-module
`_toml_escape` only escaped backslash and double-quote, not control characters. A real
file's textnode Content is `Content = "\\n              "` -- i.e. an embedded newline
IS escaped as a literal backslash-n -- but a naive escaper let a RAW newline through,
producing invalid TOML that tomllib (and presumably Nett) refuses to parse. Any string
value written into an Attributes/Style table -- not just Content -- can in principle
carry control characters (multi-line labelinnerhtml, etc.), so this is a general fix,
not a textnode-only special case.
"""
from __future__ import annotations

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def toml_escape(value: str) -> str:
    out = []
    for ch in value:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return "".join(out)


def toml_str(value: str) -> str:
    return f'"{toml_escape(value)}"'
