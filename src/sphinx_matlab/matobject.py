from typing import ClassVar, Protocol
from collections import OrderedDict
from dataclasses import dataclass

from matlab_ns.namespace_node import NamespaceNodeType
from textmate_grammar.elements import ContentElement


def get_matobject(element: ContentElement, node_type: NamespaceNodeType) -> dict:
    if element is None:
        return {}

    match node_type:
        case NamespaceNodeType.FUNCTION:
            return Function(element)
        case NamespaceNodeType.SCRIPT:
            return Script(element)
        case _:
            return {}


def parse_comment_docstring(lines: list[str]) -> str:
    if not lines:
        return ""
    padding = [len(line) - len(line.lstrip()) for line in lines]
    indent = min([pad for pad, line in zip(padding, lines) if not (line.isspace() or not line)])
    docstring = ""
    for line in [line[indent:] if len(line) >= pad else line for line, pad in zip(lines, padding)]:
        docstring += "\n" if line.isspace() or not line else line.rstrip() + " "
    return docstring.strip()


class MatObject(Protocol):
    doc: ClassVar[str]
    _textmate_token = ""

    def validate_token(self, element: ContentElement) -> None:
        if self._textmate_token and self._textmate_token != element.token:
            raise ValueError


class Script(MatObject):
    _textmate_token = ""

    def __init__(self, element: ContentElement, **kwargs) -> None:
        self.validate_token(element)
        self._element = element

        docstring_lines: list[str] = []
        for function_item, _ in element.find(
            ["comment.line.percentage.matlab", "comment.block.percentage.matlab"],
            stop_tokens="*",
            verbosity=1,
        ):
            if function_item.token == "comment.block.percentage.matlab":
                # Block comments will take precedence over single % comments

                bracket = function_item.content.index("%{") + 2
                begin = function_item.content[bracket:].index("\n") + bracket + 1
                docstring_lines = function_item.content[
                    begin : function_item.content.index("%}")
                ].split("\n")
                break

            else:
                docstring_lines.append(
                    function_item.content[function_item.content.index("%") + 1 :]
                )

        self.doc = parse_comment_docstring(docstring_lines)


@dataclass
class ArgumentAttributes:
    Output: bool = False
    Repeating: bool = False


@dataclass
class PropertyAttributes:
    hidden: bool = False


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

        if docstring_lines is None:
            docstring_lines = []

        if element.end:
            default_elements = element.findall(
                "*",
                stop_tokens=[
                    "comment.line.percentage.matlab",
                    "comment.block.percentage.matlab",
                    "comment.line.double-percentage.matlab",
                ],
                attribute="end",
            )
            if (
                default_elements
                and default_elements[0][0].token == "keyword.operator.assignment.matlab"
            ):
                self.default = "".join([el.content for el, _ in default_elements[1:]])

            doc_elements = element.findall("comment.line.percentage.matlab", attribute="end")

            self.doc = parse_comment_docstring(
                docstring_lines + [""] + [el.content[1:] for el, _ in doc_elements]
            )
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

    def __init__(self, element: ContentElement) -> None:
        self.validate_token(element)
        self._element = element

        self.input: OrderedDict[Property | str] = OrderedDict()
        self.nvpairs: dict[Property | str] = dict()
        self.output: OrderedDict[Property | str] = OrderedDict()

        docstring_lines: list[str] = []

        for function_item, _ in element.find(
            [
                "meta.function.declaration.matlab",
                "comment.line.percentage.matlab",
                "comment.block.percentage.matlab",
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

            elif function_item.token == "comment.line.percentage.matlab":
                docstring_lines.append(
                    function_item.content[function_item.content.index("%") + 1 :]
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
                        docstring, argument_doc_parts = (
                            parse_comment_docstring(argument_doc_parts),
                            [],
                        )
                        self._add_argument(arg_item, attributes, docstring)

        self._doc = parse_comment_docstring(docstring_lines)

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
                self.nvpairs[argument.name] = argument
            else:
                self.input[argument.name] = argument

    @property
    def doc(self, show_arguments: bool = False) -> str:
        docstring = self._doc
        if show_arguments:
            docstring += "\nTODO add argments"
        return docstring
