import typing

from tabulate import tabulate
from textmate_grammar.elements import ContentElement

if typing.TYPE_CHECKING:
    from .objects import Property


def _codetick(renderer: str = "rst") -> str:
    return "``" if renderer == "rst" else "`"


def append_comment(item: ContentElement, docstring_lines: list[str]) -> list[str]:
    docstring_lines.append(item.content[item.content.index("%") + 1 :])
    return docstring_lines


def append_section_comment(item: ContentElement, docstring_lines: list[str]) -> list[str]:
    docstring_lines.append(item.content[item.content.index("%%") + 2 :])
    return docstring_lines


def append_block_comment(item: ContentElement) -> list[str]:
    bracket = item.content.index("%{") + 2
    begin = item.content[bracket:].index("\n") + bracket + 1
    docstring_lines = item.content[begin : item.content.index("%}")].split("\n")
    return docstring_lines


def append_validation_table(
    validation_table: dict[str, "Property"],
    docstring: str = "",
    renderer: str = "rst",
    title: str = "Properties",
) -> str:
    codetick = _codetick(renderer)

    docstring += "\n\n"
    docstring += f"{title}\n{'-'*len(title)}\n" if renderer == "rst" else f"## {title}\n"
    table = []
    headers = ["name", "type", "doc", "default"]
    for name, arg in validation_table.items():
        arg_doc = arg._doc.replace("\n", " ") if arg._doc else None
        arg_type = arg.type if arg.type else None
        arg_default = f"{codetick}{arg.default}{codetick}" if arg.default else None
        table.append([name, arg_type, arg_doc, arg_default])
    validation_docstring = tabulate(
        table, headers=headers, tablefmt="github" if renderer != "rst" else "rst"
    )
    docstring += validation_docstring
    return docstring


def append_enum_table(
    enum_table: dict[str, tuple[str, str]],
    docstring: str = "",
    renderer: str = "rst",
    title: str = "Enumeration",
) -> str:
    codetick = _codetick(renderer)
    docstring += "\n\n"
    docstring += f"{title}\n{'-'*len(title)}\n" if renderer == "rst" else f"## {title}\n"
    table = []
    headers = ["name", "value", "doc"]
    for enum_name, (value, doc) in enum_table.items():
        enum_value = f"{codetick}{value}{codetick}" if value else None
        enum_doc = doc if doc else None
        table.append([enum_name, enum_value, enum_doc])
    enum_docstring = tabulate(
        table, headers=headers, tablefmt="github" if renderer != "rst" else "rst"
    )
    docstring += enum_docstring
    return docstring


def parse_comment_docstring(lines: list[str]) -> str:
    if not lines:
        return ""
    padding = [len(line) - len(line.lstrip()) for line in lines]
    indent = min([pad for pad, line in zip(padding, lines) if not (line.isspace() or not line)])
    docstring = ""
    for line in [line[indent:] if len(line) >= pad else line for line, pad in zip(lines, padding)]:
        docstring += "\n" if line.isspace() or not line else line.rstrip() + " "
    return docstring.strip()
