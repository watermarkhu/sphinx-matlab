import typing as t

from sphinx.application import Sphinx

from . import __version__
from .config import CONFIG_PREFIX, Config


def setup(app: Sphinx):
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
    }


def create_namespace_from_path(app: Sphinx):
    return
