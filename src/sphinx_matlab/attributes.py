from dataclasses import dataclass


class Attributes:
    @classmethod
    def from_dict(cls, settings: dict):
        for key, value in settings.items():
            if value is None:
                settings[key] = True
                continue
            annotation = cls.__annotations__.get(key)
            match annotation.__qualname__:
                case "bool":
                    if value in ["True", "true", "t", 1]:
                        settings[key] = True
                    else:
                        settings[key] = False
                case "int":
                    settings[key] = int(value)
        return cls(**settings)


@dataclass
class ArgumentAttributes(Attributes):
    """Argument block attributes
    https://mathworks.com/help/matlab/ref/arguments.html
    """

    Output: bool = False
    Repeating: bool = False


@dataclass
class PropertyAttributes(Attributes):
    """Class property attributes
    https://mathworks.com/help/matlab/matlab_oop/property-attributes.html
    """

    Abortset: bool = False
    Abstract: bool = False
    Access: str = "public"
    Constant: bool = False
    Dependent: bool = False
    GetAccess: str = "public"
    GetObservable = False
    Hidden: bool = False
    NonCopyable: bool = False
    PartialMatchPriority: int = 1
    SetAccess: str = "public"
    SetObservable: bool = False
    Transient: bool = False


class ClassdefAttributes(Attributes):
    """Class attributes
    https://mathworks.com/help/matlab/matlab_oop/class-attributes.html
    """

    Abstract: bool = False
    AllowedSubclasses: str = ""
    ConstructOnLoad: bool = False
    HandleCompatible: bool = False
    Hidden: bool = False
    InferiorClasses: str = ""
    Sealed: bool = False
