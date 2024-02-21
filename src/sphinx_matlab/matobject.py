from abc import ABC
from collections import OrderedDict
from dataclasses import dataclass
from typing import ClassVar, Protocol

from matlab_ns.namespace_node import NamespaceNode, NamespaceNodeType
from tabulate import tabulate
from textmate_grammar.elements import ContentElement

from .attributes import ArgumentAttributes, ClassdefAttributes, PropertyAttributes


class MatObject(Protocol):
    doc: ClassVar[str]
    _textmate_token = ""

    def validate_token(self, element: ContentElement) -> None:
        if self._textmate_token and self._textmate_token != element.token:
            raise ValueError


def get_matobject(node: NamespaceNode) -> MatObject | None:
    """Returns the appropiate MATLAB object based on the NamespaceNode

    Args:
        node (NamespaceNode): The matlab-ns node object

    Returns:
        MatObject | None: The
    """
    if node._element is None:
        return None

    match node.node_type:
        case NamespaceNodeType.FUNCTION:
            return Function(node)
        case NamespaceNodeType.SCRIPT:
            return Script(node)
        case NamespaceNodeType.CLASS:
            return Classdef(node)
        case _:
            return None


def parse_comment_docstring(lines: list[str]) -> str:
    if not lines:
        return ""
    padding = [len(line) - len(line.lstrip()) for line in lines]
    indent = min([pad for pad, line in zip(padding, lines) if not (line.isspace() or not line)])
    docstring = ""
    for line in [line[indent:] if len(line) >= pad else line for line, pad in zip(lines, padding)]:
        docstring += "\n" if line.isspace() or not line else line.rstrip() + " "
    return docstring.strip()


class Script(MatObject):
    _textmate_token = ""

    def __init__(self, node: NamespaceNode, **kwargs) -> None:
        self.validate_token(node._element)
        self.node = node
        self.element = node._element

        docstring_lines: list[str] = []
        for function_item, _ in node._element.find(
            [
                "comment.line.percentage.matlab",
                "comment.line.double-percentage.matlab",
                "comment.block.percentage.matlab",
            ],
            stop_tokens="*",
            verbosity=1,
        ):
            if function_item.token == "comment.line.percentage.matlab":
                docstring_lines.append(
                    function_item.content[function_item.content.index("%") + 1 :]
                )
            elif function_item.token == "comment.line.double-percentage.matlab":
                docstring_lines.append(
                    function_item.content[function_item.content.index("%%") + 2 :]
                )
            else:
                # Block comments will take precedence over single % comments

                bracket = function_item.content.index("%{") + 2
                begin = function_item.content[bracket:].index("\n") + bracket + 1
                docstring_lines = function_item.content[
                    begin : function_item.content.index("%}")
                ].split("\n")
                break

        self.doc = parse_comment_docstring(docstring_lines)


class Property(MatObject):
    _textmate_token = "meta.assignment.definition.property.matlab"

    def __init__(
        self,
        element: ContentElement,
        attributes: PropertyAttributes | ArgumentAttributes,
        docstring_lines: list[str] | None = None,
        **kwargs,
    ) -> None:
        self.validate_token(element)
        self.element = element
        self._attributes = attributes

        self.name: str = element.begin[0].content
        self.size: list[str] = []
        self.type: str = ""
        self.validators: list[str] = []
        self.default: str = ""

        if element.end:
            default_elements = element.findall(
                "*",
                stop_tokens=[
                    "comment.line.percentage.matlab",
                    "comment.block.percentage.matlab",
                    "comment.line.double-percentage.matlab",
                ],
                attribute="end",
                verbosity=1,
            )
            if (
                default_elements
                and default_elements[0][0].token == "keyword.operator.assignment.matlab"
            ):
                self.default = "".join([el.content for el, _ in default_elements[1:]])

            doc_elements = element.findall("comment.line.percentage.matlab", attribute="end")
            lines = [el.content[1:] for el, _ in doc_elements]
            if docstring_lines:
                lines += [""] + docstring_lines

            self.doc = parse_comment_docstring(lines)
        else:
            self.doc = parse_comment_docstring(docstring_lines)

        for expression, _ in element.find(
            [
                "storage.type.matlab",
                "meta.parens.size.matlab",
                "meta.block.validation.matlab",
            ],
            verbosity=1,
        ):
            if expression.token == "storage.type.matlab":
                self.type = expression.content
            elif expression.token == "meta.parens.size.matlab":
                self.size = expression.content.split(",")
            else:
                self.validators = [validator.content for validator in expression.children]


class Function(MatObject):
    _textmate_token = "meta.function.matlab"

    def __init__(self, node: NamespaceNode) -> None:
        self.validate_token(node._element)
        self.node = node
        self.element = node._element

        self.input: OrderedDict[str, Property | str] = OrderedDict()
        self.options: dict[str, Property | str] = dict()
        self.output: OrderedDict[str, Property | str] = OrderedDict()

        docstring_lines: list[str] = []

        for function_item, _ in node._element.find(
            [
                "meta.function.declaration.matlab",
                "comment.line.percentage.matlab",
                "comment.block.percentage.matlab",
                "comment.line.double-percentage.matlab",
                "meta.arguments.matlab",
            ],
            verbosity=1,
        ):
            if function_item.token == "meta.function.declaration.matlab":
                # Get input and output arguments from function declaration

                for variable, _ in function_item.find(
                    ["variable.parameter.output.matlab", "variable.parameter.input.matlab"]
                ):
                    if variable.token == "variable.parameter.input.matlab":
                        self.input[variable.content] = variable.content
                    else:
                        self.output[variable.content] = variable.content

            elif function_item.token == "comment.block.percentage.matlab":
                # Block comments will take precedence over single % comments

                bracket = function_item.content.index("%{") + 2
                begin = function_item.content[bracket:].index("\n") + bracket + 1
                docstring_lines = function_item.content[
                    begin : function_item.content.index("%}")
                ].split("\n")

            elif function_item.token in ["comment.line.percentage.matlab"]:
                docstring_lines.append(
                    function_item.content[function_item.content.index("%") + 1 :]
                )

            elif function_item.token in ["comment.line.double-percentage.matlab"]:
                docstring_lines.append(
                    function_item.content[function_item.content.index("%%") + 2 :]
                )

            else:  # meta.arguments.matlab
                modifiers = {
                    m.content: True
                    for m, _ in function_item.findall(
                        "storage.modifier.arguments.matlab", attribute="begin"
                    )
                }
                attributes = ArgumentAttributes(**modifiers)

                argument, argument_doc_parts = None, []
                for arg_item, _ in function_item.find(
                    [
                        "meta.assignment.definition.property.matlab",
                        "comment.line.percentage.matlab",
                    ],
                    verbosity=1,
                ):
                    if arg_item.token == "meta.assignment.definition.property.matlab":
                        if argument:
                            self._add_argument(argument, attributes, argument_doc_parts)

                        argument_doc_parts = []
                        argument = arg_item
                    else:
                        argument_doc_parts.append(
                            arg_item.content[arg_item.content.index("%") + 1 :]
                        )
                else:
                    if argument:
                        self._add_argument(argument, attributes, argument_doc_parts)
                        argument_doc_parts = []

        self.doc = parse_comment_docstring(docstring_lines)

    def _add_argument(
        self,
        arg_item: ContentElement,
        attributes: ArgumentAttributes | PropertyAttributes,
        docstring_lines: list[str],
    ):
        argument = Property(arg_item, attributes=attributes, docstring_lines=docstring_lines)

        if attributes.Output:
            self.output[argument.name] = argument
        else:
            if "." in argument.name:
                self.input.pop(argument.name.split(".")[0], None)
                argument.name = argument.name.split(".")[1]
                self.options[argument.name] = argument
            else:
                self.input[argument.name] = argument

    def get_doc(
        self, show_arguments: bool = False, show_options_table: bool = False, renderer: str = "md"
    ) -> str:
        codetick = "``" if renderer == "rst" else "`"

        docstring = self.doc
        if not show_arguments:
            return docstring

        if self.input:
            docstring += "\n"
        for argument in self.input.values():
            if isinstance(argument, str):
                docstring += f"\n:param {argument}:"
            else:
                doc = argument.doc.replace("\n", " ")
                docstring += "\n:param "
                if argument.type:
                    docstring += argument.type
                docstring += f" {argument.name}: {doc}"
                if argument.default:
                    docstring += f" Defaults to {codetick}{argument.default}{codetick}"

        if show_options_table and self.options:
            docstring += "\n\n"
            docstring += (
                "Name-value pairs\n----------------\n"
                if renderer == "rst"
                else "## Name-value pairs\n"
            )
            table = []
            headers = ["name", "type", "doc", "default"]
            for name, argument in self.options.items():
                doc = argument.doc.replace("\n", " ")
                table.append([name, argument.type, doc, f"{codetick}{argument.default}{codetick}"])
            options_table = tabulate(
                table, headers=headers, tablefmt="github" if renderer != "rst" else "rst"
            )
            docstring += options_table

        # TODO output arguments
        return docstring


class Classdef(MatObject):
    _textmate_token = "meta.class.matlab"

    def __init__(self, node: NamespaceNode) -> None:
        self.validate_token(node._element)
        self.node = node

        self.attributes = None
        self.enumeration: str = ""
        self.methods: dict[str, Function] = dict()
        self.properties: dict[str, Property] = dict()

        docstring_lines: list[str] = []

        for class_item, _ in node._element.find(
            [
                "meta.class.declaration.matlab",
                "comment.line.percentage.matlab",
                "comment.block.percentage.matlab",
                "comment.line.double-percentage.matlab",
                "meta.properties.matlab",
                "meta.methods.matlab",
                "meta.enum.matlab"
            ],
            verbosity=1,
        ):
            return
