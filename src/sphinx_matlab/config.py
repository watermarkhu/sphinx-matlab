import dataclasses as dc
import typing as t


CONFIG_PREFIX = "matlab_"


@dc.dataclass
class Config:

    path: list[str] = dc.field(
        default_factory=list,
        metadata={
            "help": "The MATLAB path variable, which defines the namespace.",
            "sphinx_type": list,
            "category": "required"
        }
    )

    def as_triple(self) -> t.Iterable[tuple[str, t.Any, dc.Field]]:  # type: ignore[type-arg]
        """Yield triples of (name, value, field)."""
        fields = {f.name: f for f in dc.fields(self.__class__)}
        for name, value in dc.asdict(self).items():
            yield name, value, fields[name]