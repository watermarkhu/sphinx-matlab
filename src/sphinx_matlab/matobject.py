from abc import ABC
from collections import OrderedDict
from dataclasses import dataclass
from typing import ClassVar, Protocol

from matlab_ns.namespace_node import NamespaceNode, NamespaceNodeType
from tabulate import tabulate
from textmate_grammar.elements import ContentBlockElement, ContentElement

from .attributes import ArgumentAttributes, ClassdefAttributes, MethodAttributes, PropertyAttributes

_COMMENT_TOKENS = [
    "comment.line.percentage.matlab",
    "comment.block.percentage.matlab",
    "comment.line.double-percentage.matlab",
]


class MatObject(Protocol):
    doc: ClassVar[str]
    _textmate_token: str = ""

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


def _append_comment(item: ContentElement, docstring_lines: list[str]) -> list[str]:
    docstring_lines.append(item.content[item.content.index("%") + 1 :])
    return docstring_lines


def _append_section_comment(item: ContentElement, docstring_lines: list[str]) -> list[str]:
    docstring_lines.append(item.content[item.content.index("%%") + 2 :])
    return docstring_lines


def _append_block_comment(item: ContentElement) -> list[str]:
    bracket = item.content.index("%{") + 2
    begin = item.content[bracket:].index("\n") + bracket + 1
    docstring_lines = item.content[begin : item.content.index("%}")].split("\n")
    return docstring_lines


def _parse_comment_docstring(lines: list[str]) -> str:
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
        for function_item, _ in node._element.find(_COMMENT_TOKENS, stop_tokens="*", depth=1):
            if function_item.token == "comment.line.percentage.matlab":
                _append_comment(function_item, docstring_lines)
            elif function_item.token == "comment.line.double-percentage.matlab":
                _append_section_comment(function_item, docstring_lines)
            else:
                # Block comments will take precedence over single % comments

                bracket = function_item.content.index("%{") + 2
                begin = function_item.content[bracket:].index("\n") + bracket + 1
                docstring_lines = function_item.content[
                    begin : function_item.content.index("%}")
                ].split("\n")
                break

        self.doc = _parse_comment_docstring(docstring_lines)


class Property(MatObject):
    _textmate_token = "meta.assignment.definition.property.matlab"

    def __init__(
        self,
        element: ContentBlockElement,
        attributes: PropertyAttributes | ArgumentAttributes,
        docstring_lines: list[str] | None = None,
        **kwargs,
    ) -> None:
        if docstring_lines is None:
            docstring_lines = []

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
                stop_tokens=_COMMENT_TOKENS,
                attribute="end",
                depth=1,
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

            self.doc = _parse_comment_docstring(lines)
        else:
            self.doc = _parse_comment_docstring(docstring_lines)

        for expression, _ in element.find(
            [
                "storage.type.matlab",
                "meta.parens.size.matlab",
                "meta.block.validation.matlab",
            ],
            depth=1,
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
        self._process_elements(node._element)

    def _process_elements(self, element: ContentBlockElement):
        self.input: OrderedDict[str, Property | str] = OrderedDict()
        self.options: dict[str, Property] = dict()
        self.output: OrderedDict[str, Property | str] = OrderedDict()

        docstring_lines: list[str] = []

        for function_item, _ in element.find(
            [
                "meta.function.declaration.matlab",
                "meta.arguments.matlab",
            ]
            + _COMMENT_TOKENS,
            depth=1,
        ):
            if function_item.token == "meta.function.declaration.matlab":
                # Get input and output arguments from function declaration

                for variable, _ in function_item.find(
                    [
                        "entity.name.function.matlab",
                        "variable.parameter.output.matlab",
                        "variable.parameter.input.matlab",
                    ]
                ):
                    if variable.token == "entity.name.function.matlab":
                        self.local_name = variable.content
                    elif variable.token == "variable.parameter.input.matlab":
                        self.input[variable.content] = variable.content
                    else:
                        self.output[variable.content] = variable.content

            elif function_item.token == "comment.block.percentage.matlab":
                docstring_lines = _append_block_comment(function_item)

            elif function_item.token == "comment.line.percentage.matlab":
                _append_comment(function_item, docstring_lines)

            elif function_item.token == "comment.line.double-percentage.matlab":
                _append_section_comment(function_item, docstring_lines)

            else:  # meta.arguments.matlab
                modifiers = {
                    m.content: True
                    for m, _ in function_item.findall(
                        "storage.modifier.arguments.matlab", attribute="begin"
                    )
                }
                attributes = ArgumentAttributes(**modifiers)

                arg = None
                arg_doc_parts: list[str] = []

                for arg_item, _ in function_item.find(
                    [
                        "meta.assignment.definition.property.matlab",
                        "comment.line.percentage.matlab",
                    ],
                    depth=1,
                ):
                    if arg_item.token == "meta.assignment.definition.property.matlab":
                        if arg:
                            self._add_argument(arg, attributes, arg_doc_parts)

                        arg_doc_parts = []
                        arg = arg_item
                    else:
                        arg_doc_parts.append(arg_item.content[arg_item.content.index("%") + 1 :])
                else:
                    if arg:
                        self._add_argument(arg, attributes, arg_doc_parts)
                        arg_doc_parts = []

        self.doc = _parse_comment_docstring(docstring_lines)

    def _add_argument(
        self,
        arg_item: ContentBlockElement,
        attributes: ArgumentAttributes,
        docstring_lines: list[str],
    ):
        arg = Property(arg_item, attributes=attributes, docstring_lines=docstring_lines)

        if attributes.Output:
            self.output[arg.name] = arg
        else:
            if "." in arg.name:
                self.input.pop(arg.name.split(".")[0], None)
                arg.name = arg.name.split(".")[1]
                self.options[arg.name] = arg
            else:
                self.input[arg.name] = arg

    def get_doc(
        self, show_arguments: bool = False, show_options_table: bool = False, renderer: str = "md"
    ) -> str:
        codetick = "``" if renderer == "rst" else "`"

        docstring = self.doc
        if not show_arguments:
            return docstring

        if self.input:
            docstring += "\n"
        for arg in self.input.values():
            if isinstance(arg, str):
                docstring += f"\n:param {arg}:"
            else:
                doc = arg.doc.replace("\n", " ")
                docstring += "\n:param "
                if arg.type:
                    docstring += arg.type
                docstring += f" {arg.name}: {doc}"
                if arg.default:
                    docstring += f" Defaults to {codetick}{arg.default}{codetick}"

        if show_options_table and self.options:
            docstring += "\n\n"
            docstring += (
                "Name-value pairs\n----------------\n"
                if renderer == "rst"
                else "## Name-value pairs\n"
            )
            table = []
            headers = ["name", "type", "doc", "default"]
            for name, arg in self.options.items():
                arg_doc = arg.doc.replace("\n", " ") if arg.doc else None
                arg_type = arg.type if arg.type else None
                arg_default = f"{codetick}{arg.default}{codetick}" if arg.default else None
                table.append([name, arg_type, arg_doc, arg_default])
            options_table = tabulate(
                table, headers=headers, tablefmt="github" if renderer != "rst" else "rst"
            )
            docstring += options_table

        # TODO output arguments
        return docstring


class Method(Function):
    def __init__(
        self, element: ContentBlockElement, attributes: MethodAttributes, classdef: "Classdef"
    ):
        self.validate_token(element)
        self.element = element
        self.attributes = attributes
        self.classdef = classdef
        self._process_elements(element)

        if self.local_name != classdef.local_name or not attributes.Static:
            self.input.popitem(last=False)


class Classdef(MatObject):
    _textmate_token = "meta.class.matlab"

    def __init__(self, node: NamespaceNode) -> None:
        self.validate_token(node._element)
        self.node = node

        self.local_name: str = ""
        self.ancestors: list[str] = []
        self.attributes = None
        self.enumeration: dict[str, (str, str)] = dict()
        self.methods: dict[str, Method] = dict()
        self.properties: dict[str, Property] = dict()

        docstring_lines: list[str] = []

        for class_item, _ in node._element.find(
            [
                "meta.class.declaration.matlab",
                "meta.properties.matlab",
                "meta.enum.matlab",
                "meta.methods.matlab",
            ]
            + _COMMENT_TOKENS,
            depth=1,
        ):
            if class_item.token == "meta.class.declaration.matlab":
                for declation_item, _ in class_item.find("*", depth=1):
                    if declation_item.token == "entity.name.type.class.matlab":
                        self.local_name = declation_item.content
                    elif declation_item.token == "meta.inherited-class.matlab":
                        self.ancestors.append(declation_item.content)
                    elif declation_item.token == "punctuation.definition.comment.matlab":
                        docstring_lines.append(
                            class_item.content[class_item.content.index("%") + 1 :]
                        )
            elif class_item.token == "comment.block.percentage.matlab":
                docstring_lines = _append_block_comment(class_item)

            elif class_item.token == "comment.line.percentage.matlab":
                _append_comment(class_item, docstring_lines)

            elif class_item.token == "comment.line.double-percentage.matlab":
                _append_section_comment(class_item, docstring_lines)

            elif class_item.token == "meta.properties.matlab":
                modifiers = {}
                current_modifier, current_value = "", True
                for modifier_item, _ in class_item.findall("*", attribute="begin"):
                    if modifier_item.token == "storage.modifier.properties.matlab":
                        if current_modifier:
                            modifiers[current_modifier], current_value = current_value, True
                        current_modifier = modifier_item.content
                    elif modifier_item.token == "keyword.operator.assignment.matlab":
                        current_value = ""
                    elif (
                        modifier_item.token
                        not in ["keyword.control.properties.matlab"] + _COMMENT_TOKENS
                    ):
                        current_value += modifier_item.content
                else:
                    if current_modifier:
                        modifiers[current_modifier] = current_value

                attributes = PropertyAttributes.from_dict(modifiers)

                prop = None
                prop_doc_parts: list[str] = []
                for prop_item, _ in class_item.find(
                    [
                        "meta.assignment.definition.property.matlab",
                        "comment.line.percentage.matlab",
                    ],
                    depth=1,
                ):
                    if prop_item.token == "meta.assignment.definition.property.matlab":
                        if prop:
                            self._add_prop(prop, attributes, prop_doc_parts)

                        prop_doc_parts = []
                        prop = prop_item
                    else:
                        prop_doc_parts.append(prop_item.content[prop_item.content.index("%") + 1 :])
                else:
                    if prop:
                        self._add_prop(prop, attributes, prop_doc_parts)
                        prop_doc_parts = []

            elif class_item.token == "meta.enum.matlab":
                enum_doc_parts: list[str] = []
                enum_name: str = ""
                enum_value: str = ""
                for enum_item, _ in class_item.find(
                    [
                        "meta.assignment.definition.enummember.matlab",
                        "meta.parens.matlab",
                        "comment.line.percentage.matlab",
                    ],
                    attribute="children",
                ):
                    if enum_item.token == "meta.assignment.definition.enummember.matlab":
                        if enum_name:
                            enum_doc = _parse_comment_docstring(enum_doc_parts)
                            self.enumeration[enum_name] = (enum_value, enum_doc)
                            enum_doc_parts, enum_value = [], ""
                        enum_name = next(enum_item.find("variable.other.enummember.matlab"))[
                            0
                        ].content

                    elif enum_item.token == "meta.parens.matlab":
                        enum_value = enum_item.content[1:-1]
                    else:
                        _append_comment(enum_item, enum_doc_parts)
                else:
                    if enum_name:
                        enum_doc = _parse_comment_docstring(enum_doc_parts)
                        self.enumeration[enum_name] = (enum_value, enum_doc)
                        enum_doc_parts, enum_value = [], ""

            else:
                modifiers = {}
                current_modifier, current_value = "", True
                for modifier_item, _ in class_item.findall(
                    ["storage.modifier.methods.matlab", "storage.modifier.access.matlab"],
                    attribute="begin",
                ):
                    if modifier_item.token == "storage.modifier.methods.matlab":
                        if current_modifier:
                            modifiers[current_modifier], current_value = current_value, True
                        current_modifier = modifier_item.content
                    else:
                        current_value = modifier_item.content
                else:
                    if current_modifier:
                        modifiers[current_modifier] = current_value

                attributes = MethodAttributes.from_dict(modifiers)

                for method_item, _ in class_item.find("meta.function.matlab", depth=1):
                    method = Method(method_item, attributes, self)
                    self.methods[method.local_name] = method

        self.doc = _parse_comment_docstring(docstring_lines)

    def get_doc(self, renderer: str = "md") -> str:
        codetick = "``" if renderer == "rst" else "`"

        docstring = self.doc

        if self.enumeration:
            docstring += "\n\n"
            docstring += "Enumeration\n-----------\n" if renderer == "rst" else "## Enumeration\n"
            table = []
            headers = ["name", "value", "doc"]
            for enum_name, (value, doc) in self.enumeration.items():
                enum_value = f"{codetick}{value}{codetick}" if value else None
                enum_doc = doc if doc else None
                table.append([enum_name, enum_value, enum_doc])
            enum_table = tabulate(
                table, headers=headers, tablefmt="github" if renderer != "rst" else "rst"
            )
            docstring += enum_table

        return docstring

    def _add_prop(
        self,
        prop_item: ContentBlockElement,
        attributes: ArgumentAttributes | PropertyAttributes,
        docstring_lines: list[str],
    ):
        prop = Property(prop_item, attributes=attributes, docstring_lines=docstring_lines)
        self.properties[prop.name] = prop
