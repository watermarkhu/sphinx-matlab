import enum
import typing as t

from docutils.nodes import Element
from sphinx.application import Sphinx
from sphinx.util import logging

from .config import CONFIG_PREFIX, Config, ValidationError

LOGGER = logging.getLogger("autodoc2")


class WarningSubtypes(enum.Enum):
    """The subtypes of warnings for the extension."""

    CONFIG_ERROR = "config_error"
    """Issue with configuration validation."""
    GIT_CLONE_FAILED = "git_clone"
    """Failed to clone a git repository."""
    MISSING_PATH = "unknown_path"
    """If the path item does not exist."""
    DUPLICATE_ITEM = "dup_item"
    """Duplicate fully qualified name found during package analysis."""
    RENDER_ERROR = "render"
    """Generic rendering error."""
    ALL_MISSING = "all_missing"
    """__all__ attribute missing or empty in a module."""
    ALL_RESOLUTION = "all_resolve"
    """Issue with resolution of an item in a module's __all__ attribute."""
    NAME_NOT_FOUND = "missing"


def load_config(
    app: Sphinx,
    *,
    overrides: None | dict[str, t.Any] = None,
    location: None | Element = None,
) -> Config:
    """Load the configuration."""
    values: dict[str, t.Any] = {}
    overrides = overrides or {}
    config_fields = {name: field for name, _, field in Config().as_triple()}
    # check if keys in overrides are valid
    difference = set(overrides.keys()) - set(config_fields.keys())
    if difference:
        warn_sphinx(
            f"Unknown configuration keys: {', '.join(difference)}",
            WarningSubtypes.CONFIG_ERROR,
            location,
        )
    for name, field in config_fields.items():
        sphinx_name = f"{CONFIG_PREFIX}{name}"
        value = overrides.get(name, app.config[sphinx_name])
        if "sphinx_validate" in field.metadata:
            try:
                value = field.metadata["sphinx_validate"](sphinx_name, value)
            except ValidationError as err:
                warn_sphinx(str(err), WarningSubtypes.CONFIG_ERROR, location)
                continue
        values[name] = value
    return Config(**values)


def warn_sphinx(msg: str, subtype: WarningSubtypes, location: None | Element = None) -> None:
    """Log a warning in Sphinx."""
    LOGGER.warning(
        f"{msg} [autodoc2.{subtype.value}]",
        type="autodoc2",
        subtype=subtype.value,
        location=location,
    )
