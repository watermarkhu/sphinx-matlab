import typing as t
from pathlib import Path

from matlab_ns import Workspace
from sphinx.application import Sphinx

from . import __version__
from .config import CONFIG_PREFIX, Config
from .matobject import get_matobject
from .utils import WarningSubtypes, load_config, warn_sphinx


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

    app.connect("builder-inited", create_namespace)
    return {
        "version": __version__,
        # "env_version": "hash_based_on_filetree",
        "parallel_write_safe": True,
    }


def create_namespace(app: Sphinx) -> None:
    config = load_config(app)
    workspace = Workspace()
    confdir = Path(app.confdir)

    qualified_path = []
    for path in config.path:
        if (confdir / path).exists():
            qualified_path.append((confdir / path).resolve())
        elif Path(path).exists():
            qualified_path.append(Path(path).resolve())
        else:
            warn_sphinx(
                f"Configured path does not exist: {path}",
                WarningSubtypes.MISSING_PATH,
            )
    workspace.init_namespace(qualified_path)
    app.env.workspace = workspace

    node = app.env.workspace.find_symbol("argumentValidation")
    metadata = get_matobject(node._element, node.node_type)
    return
