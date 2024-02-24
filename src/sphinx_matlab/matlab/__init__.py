from matlab_ns.namespace_node import NamespaceNode, NamespaceNodeType

from .objects import Classdef, Function, MatObject, Script


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
