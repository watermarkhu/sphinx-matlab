from sphinx.application import Sphinx
import typing as t

from . import __version__
from .config import Config, CONFIG_PREFIX


def _setup(app: Sphinx):
    for name, default, field in Config().as_triple():
        sphinx_type = t.Any
        if "sphinx_type" in field.metadata:
            sphinx_type = field.metadata["sphinx_type"]
            if sphinx_type in (str, int, float, bool, list):
                sphinx_type = (sphinx_type,)
        app.add_config_value(
            f"{CONFIG_PREFIX}{name}",
            field.metadata.get("sphinx_default", default),
            "env",
            types=sphinx_type,
        )

    app.connect("builder-inited", create_namespace_from_path)
    return {
        "version": __version__,
        # "env_version": "hash_based_on_filetree",
        "parallel_write_safe": True,
        "parallel_write_safe": False
    }


def create_namespace_from_path(app: Sphinx):
    return