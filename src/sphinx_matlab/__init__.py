"""This is the sphinx_matlab module"""

from sphinx.application import Sphinx


__version__ = "0.1.0"


def setup(app: Sphinx):
    from .extension import _setup
    return _setup(app)