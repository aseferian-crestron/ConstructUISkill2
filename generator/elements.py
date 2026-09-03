"""
{PageAttributes} [[Elements]] tree builder -- Phase 3.

Grounded directly in C:\\Git\\CCIDE\\Crestron.IDE\\Projects\\UiEditor\\UiEditor.Server\\Models\\ElementSource.cs
and confirmed against real files (Component - Button.cuig, Widget.cuiw, Widget on Page.cuig).

ElementSource.cs field declaration order:
  Name, Type, Status, Content, Removable, Draggable, Highlightable, Copyable, Editable,
  Selectable, Hoverable, _InnerText, Components, Attributes, Style, Classes

Nett (the TOML library) serializes struct/class fields in declaration order EXCEPT that
TOML syntax itself requires every "simple" key (a plain value or inline array, like
`Classes = [...]`) to appear before any subtable (`[[...Components]]`, `[...Attributes]`,
`[...Style]`) within the same table body -- confirmed directly against real files: a
`widgetContainer` element's `Classes = [...]` line appears immediately after `Type`, even
though `Classes` is declared AFTER `Attributes`/`Style` in the C# class. So the real
emission order is: every non-null SCALAR field first (Name, Type, Status, Content,
Removable, Draggable, Highlightable, Copyable, Editable, Selectable, Hoverable,
_InnerText, then Classes), THEN every non-null TABLE-typed field in declaration order
(Components, Attributes, Style).

Also confirmed: a widgetContainer's OWN `[Attributes]` table is written AFTER all of its
children's `[[Components]]` blocks (a direct, source-explained consequence of the same
rule -- Attributes is declared after Components) -- this was previously only known
empirically (v1's "BUG #2"); it now falls out of the field-order rule by construction,
so a correct writer never has to special-case it.

Only null/None fields are omitted (confirmed: real elements omit Name/Status/Content
etc. entirely when unset, rather than writing empty strings) -- Nett's default
skip-null behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from toml_util import toml_str as _toml_str


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


@dataclass
class Element:
    """Mirrors ElementSource.cs. Only Type/Editable/Classes/Attributes/Components are
    exercised so far (Phase 3 scope: empty pages/widgets + widget references) -- the
    rest are modeled for completeness/future phases but left None/unset here.
    """

    type: str | None = None
    name: str | None = None
    status: str | None = None
    content: str | None = None
    removable: bool | None = None
    draggable: bool | None = None
    highlightable: int | None = None
    copyable: bool | None = None
    editable: bool | None = None
    selectable: bool | None = None
    hoverable: bool | None = None
    inner_text: bool | None = None
    classes: list[str] | None = None
    components: list["Element"] = field(default_factory=list)
    attributes: list[tuple[str, str]] = field(default_factory=list)  # ordered
    style: list[tuple[str, str]] = field(default_factory=list)  # ordered

    def to_toml_lines(self, prefix: str) -> list[str]:
        lines = [f"[[{prefix}]]"]

        # 1. every non-null SCALAR field, Classes last among scalars (see module docstring)
        scalar_fields = [
            ("Name", self.name, _toml_str),
            ("Type", self.type, _toml_str),
            ("Status", self.status, _toml_str),
            ("Content", self.content, _toml_str),
            ("Removable", self.removable, _toml_bool),
            ("Draggable", self.draggable, _toml_bool),
            ("Highlightable", self.highlightable, str),
            ("Copyable", self.copyable, _toml_bool),
            ("Editable", self.editable, _toml_bool),
            ("Selectable", self.selectable, _toml_bool),
            ("Hoverable", self.hoverable, _toml_bool),
            ("_InnerText", self.inner_text, _toml_bool),
        ]
        for key, val, fmt in scalar_fields:
            if val is not None:
                lines.append(f"{key} = {fmt(val)}")
        if self.classes:
            lines.append("Classes = [" + ", ".join(_toml_str(c) for c in self.classes) + "]")

        # 2. table-typed fields in declaration order: Components, Attributes, Style.
        # A blank line precedes EACH present region (confirmed against real files: a
        # parent's own trailing [Elements.Attributes] is preceded by a blank line even
        # though its preceding Components region already emitted one before ITS start --
        # but consecutive siblings WITHIN Components get no separating blank line at all,
        # since each child recursively handles its own internal blank lines only).
        if self.components:
            lines.append("")
            for child in self.components:
                lines.extend(child.to_toml_lines(f"{prefix}.Components"))
        if self.attributes:
            lines.append("")
            lines.append(f"[{prefix}.Attributes]")
            for k, v in self.attributes:
                lines.append(f"{k} = {_toml_str(v)}")
        if self.style:
            lines.append("")
            lines.append(f"[{prefix}.Style]")
            for k, v in self.style:
                lines.append(f"{k} = {_toml_str(v)}")

        return lines
