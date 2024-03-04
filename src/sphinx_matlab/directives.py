import typing as t

from autodoc2.sphinx.docstring import parser_options
from autodoc2.utils import WarningSubtypes
from docutils import nodes
from docutils.parsers.rst import directives, roles
from sphinx.util.docutils import SphinxDirective

from .matlab import objects as objects
from .utils import load_config, warn_sphinx

try:
    import tomllib
except ImportError:
    # python < 3.11
    import tomli as tomllib  # type: ignore


class FunctionRenderer(SphinxDirective):
    """Directive to render a function of an object."""

    has_content = False
    required_arguments = 1  # the full name
    optional_arguments = 0
    final_argument_whitespace = True

    option_spec: t.ClassVar[dict[str, t.Any]] = {
        "parser": parser_options,
        "literal": directives.flag,
        "literal-lexer": directives.unchanged,
        "literal-lineos": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        directive_source, directive_line = self.get_source_info()
        # warnings take the docname and line number
        warning_loc = (self.env.docname, directive_line)

        full_name: str = self.arguments[0]

        # Load the workspace node
        workspace = self.env.workspace
        workspace_node = workspace.find_symbol(full_name)
        if workspace_node is None:
            warn_sphinx(
                f"Could not find {full_name}",
                WarningSubtypes.NAME_NOT_FOUND,
                location=warning_loc
            )
            return []
        
        # Load the configuration with overrites
        try:
            overrides = tomllib.loads("\n".join(self.content)) if self.content else {}
        except Exception as err:
            warn_sphinx(
                f"Could not parse TOML config: {err}",
                WarningSubtypes.CONFIG_ERROR,
                location=warning_loc,
            )
        config = load_config(self.env.app, overrides=overrides, location=warning_loc)
        item = objects.Function(workspace_node)
        document = item.doc(config)

        if "literal" in self.options:
            # return the literal docstring
            literal = nodes.literal_block(text=document)
            self.set_source_info(literal)
            if "literal-lexer" in self.options:
                literal["language"] = self.options["literal-lexer"]
            if "literal-linenos" in self.options:
                literal["linenos"] = True
                literal["highlight_args"] = {"linenostart": 1 + item.offset}
            return [literal]

        pass