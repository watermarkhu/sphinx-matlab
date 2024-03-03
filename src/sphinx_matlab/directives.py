from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from .matlab import objects as objects


class FunctionRenderer(SphinxDirective):
    """Directive to render a function of an object."""

    has_content = False
    required_arguments = 1  # the full name
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:
        directive_source, directive_line = self.get_source_info()
        # warnings take the docname and line number
        warning_loc = (self.env.docname, directive_line)

        full_name: str = self.arguments[0]
        workspace = self.env.workspace
        workspace_node = workspace.find_symbol(full_name)

        pass