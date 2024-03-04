import typing as t

from autodoc2.sphinx.docstring import parser_options, parsing_context, change_source
from autodoc2.utils import WarningSubtypes
from docutils import nodes
from docutils.parsers import Parser
from docutils.parsers.rst import directives, roles
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective, new_document
from sphinx.util.logging import prefixed_warnings

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
        "literal-linenos": directives.flag,
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
        docstring = item.doc(config)

        if "literal" in self.options:
            # return the literal docstring
            literal = nodes.literal_block(text=docstring)
            self.set_source_info(literal)
            if "literal-lexer" in self.options:
                literal["language"] = self.options["literal-lexer"]
            if "literal-linenos" in self.options:
                literal["linenos"] = True
                literal["highlight_args"] = {"linenostart": 1 + item.offset}
            return [literal]
        
        source_path = str(workspace_node.full_path)
        self.env.note_dependency(source_path)

        with prefixed_warnings("[spinx-matlab]"):
            if self.options.get("parser", None):
                # parse into a dummy document and return created nodes
                parser: Parser = self.options["parser"]()
                document = new_document(
                    source_path,
                    self.state.document.settings,
                )
                document.reporter.get_source_and_line = lambda li: (
                    source_path,
                    li + item.offset,
                )
                with parsing_context():
                    parser.parse(docstring, document)
                children = document.children or []
            else:
               
                doc_lines = docstring.splitlines()
                with change_source(
                    self.state, source_path, item.offset - directive_line
                ):
                    base = nodes.Element()
                    base.source = source_path
                    base.line = item.offset
                    content = StringList(
                        doc_lines,
                        source=source_path,
                        items=[
                            (source_path, i + item.offset + 1)
                            for i in range(len(doc_lines))
                        ],
                    )
                    self.state.nested_parse(
                        content, 0, base, match_titles="allowtitles" in self.options
                    )
                children = base.children or []
        return children

        pass