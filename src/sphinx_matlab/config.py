import dataclasses as dc
import re
import typing as t

from autodoc2.config import _load_renderer
from autodoc2.render.base import RendererBase

CONFIG_PREFIX = "matlab_"


class ValidationError(Exception):
    """An error validating a config value."""


def _validate_hidden_objects(name: str, item: t.Any) -> set[str]:
    """Validate that the hidden objects config option is a set."""
    if not isinstance(item, (list, tuple, set)) or not all(isinstance(x, str) for x in item):
        raise ValidationError(f"{name!r} must be a list of string")
    value = set(item)
    _valid = {"undoc", "hidden", "private", "protected", "inherited"}
    if not value.issubset(_valid):
        raise ValidationError(f"{name!r} must be a subset of {_valid}")
    return value


def _validate_list_tuple_regex_str(name: str, item: t.Any) -> list[tuple[t.Pattern[str], str]]:
    """Validate that an item is a list of (regex, str) tuples."""
    if not isinstance(item, list) or not all(
        isinstance(x, (list, tuple)) and len(x) == 2 for x in item
    ):
        raise ValidationError(f"{name!r} must be a list of (string, string) tuples")
    compiled = []
    for i, (regex, replacement) in enumerate(item):
        try:
            compiled.append((re.compile(regex), replacement))
        except re.error as exc:
            raise ValidationError(f"{name}[{i}] is not a valid regex: {exc}") from exc
    return compiled


@dc.dataclass
class Config:
    path: list[str] = dc.field(
        default_factory=list,
        metadata={
            "help": "The MATLAB path variable, which defines the namespace.",
            "sphinx_type": list,
            "category": "required",
        },
    )

    output_dir: str = dc.field(
        default="apidocs",
        metadata={
            "help": (
                "The root output directory for the documentation, "
                "relative to the source directory (in POSIX format)."
            ),
            "sphinx_type": str,
            "category": "render",
        },
    )

    render_plugin: type[RendererBase] = dc.field(
        default_factory=(lambda: _load_renderer("render_plugin", "rst")),
        metadata={
            "help": (
                "The renderer to use for the documentation. "
                "This can be one of `rst` or `md`/`myst`, "
                "to use the built-in renderers, "
                "or a string pointing to a class that inherits from `RendererBase`, "
                "such as `mypackage.mymodule.MyRenderer`."
            ),
            "sphinx_type": str,
            "sphinx_default": "rst",
            "sphinx_validate": _load_renderer,
            "doc_type": "str",
            "category": "render",
        },
    )

    hidden_objects: set[
        t.Literal["undoc", "hidden", "private", "protected", "inherited"]
    ] = dc.field(
        default_factory=lambda: {"hidden", "private", "inherited"},
        metadata={
            "help": (
                "The default hidden items. "
                "Can contain:\n"
                "- `undoc`: undocumented objects\n"
                "- `hidden`: Hidden methods, e.g. `(Hidden)`\n"
                "- `private`: Private method, e.g. `(Access=private)`\n"
                "- `protected`: Protected method, e.g. `(Access=protected)`\n"
                "- `inherited`: inherited class methods\n"
            ),
            "sphinx_type": list,
            "sphinx_validate": _validate_hidden_objects,
            "doc_type": 'list["undoc" | "dunder" | "private" | "inherited"]',
            "category": "render",
        },
    )

    no_index: bool = dc.field(
        default=False,
        metadata={
            "help": "Do not generate a cross-reference index.",
            "sphinx_type": bool,
            "category": "render",
        },
    )

    module_summary: bool = dc.field(
        default=True,
        metadata={
            "help": "Whether to include a per-module summary.",
            "sphinx_type": bool,
            "category": "render",
        },
    )

    docstring_parser_regexes: list[tuple[t.Pattern[str], str]] = dc.field(
        default_factory=list,
        metadata={
            "help": (
                "Match fully qualified names against regexes to use a specific parser. "
                "The parser can be one of 'rst', 'myst', or the fully qualified name of a custom parser class. "
                "The first match is used."
            ),
            "sphinx_type": list,
            "sphinx_validate": _validate_list_tuple_regex_str,
            "doc_type": "list[tuple[str, str]]",
            "category": "render",
        },
    )

    argument_block_parameters: bool = dc.field(
        default=True,
        metadata={
            "help": (
                "Whether to use information from argument blocks in functions and methods "
                "to document input (and output) parameters. Any single %% comment after the "
                "argument will be treated as the argument description. \n"
                "This option does not disregard any parameters defined by the user in the "
                "function/method header docstring itself."
            ),
            "sphinx_type": bool,
            "category": "render",
        },
    )

    argument_options_table: bool = dc.field(
        default=True,
        metadata={
            "help": (
                "Whether to include the name-value pairs defined in the argument block of "
                "functions/methods in the docstring in table format."
            ),
            "sphinx_type": bool,
            "category": "render",
        },
    )

    class_docstring: t.Literal["merge", "both"] = dc.field(
        default="merge",
        metadata={
            "help": (
                "How to handle documenting of classes. "
                "If `merge`, the constructor docstring is appended to the class docstring "
                "and the constructor method is omitted."
                "If `both`, then the constructor method is included separately."
            ),
            "sphinx_type": str,
            "doc_type": '"merge" | "both"',
            "category": "render",
        },
    )

    class_properties_table: bool = dc.field(
        default=True,
        metadata={
            "help": (
                "Whether to include the publicly accessible properties of the class in the "
                "docstring in table format. Any single %% comment after the "
                "property will be treated as the property description."
            ),
            "sphinx_type": bool,
            "category": "render",
        },
    )

    class_inheritance: bool = dc.field(
        default=True,
        metadata={
            "help": "Whether to document class inheritance.",
            "sphinx_type": bool,
            "category": "render",
        },
    )

    validators: bool = dc.field(
        default=True,
        metadata={
            "help": "Whether to include validators.",
            "sphinx_type": bool,
            "category": "render",
        },
    )

    docstrings: t.Literal["all", "direct", "none"] = dc.field(
        default="direct",
        metadata={
            "help": "Which objects to include docstrings for. "
            "'direct' means only from objects that are not inherited.",
            "sphinx_type": str,
            "doc_type": '"all" | "direct"',
            "category": "render",
        },
    )

    sort_names: bool = dc.field(
        default=False,
        metadata={
            "help": "Whether to sort by name, when documenting, otherwise order by source",
            "sphinx_type": bool,
            "category": "render",
        },
    )

    def as_triple(self) -> t.Iterable[tuple[str, t.Any, dc.Field]]:  # type: ignore[type-arg]
        """Yield triples of (name, value, field)."""
        fields = {f.name: f for f in dc.fields(self.__class__)}
        for name, value in dc.asdict(self).items():
            yield name, value, fields[name]
