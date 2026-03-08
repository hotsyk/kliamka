"""Kliamka - Small Python CLI library."""

import argparse
import os
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel

__all__ = [
    "KliamkaArg",
    "KliamkaArgClass",
    "KliamkaError",
    "ParserMeta",
    "kliamka_cli",
    "kliamka_subcommands",
    "__version__",
    "__author__",
    "__email__",
]

__version__ = "0.5.0"
__author__ = "Volodymyr Hotsyk"
__email__ = "git@hotsyk.com"


class KliamkaError(Exception):
    """Base exception for kliamka library."""

    pass


F = TypeVar("F", bound=Callable[..., Any])


def _is_bool_annotation(annotation: Any) -> bool:
    """Check if annotation represents a bool type."""
    if annotation is bool:
        return True
    origin = getattr(annotation, "__origin__", None)
    if origin is Union:
        non_none = [a for a in annotation.__args__ if a is not type(None)]
        return len(non_none) == 1 and non_none[0] is bool
    return False


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Unwrap Optional[T] to (T, True) or return (annotation, False)."""
    if (
        annotation is not None
        and hasattr(annotation, "__origin__")
        and annotation.__origin__ is Union
    ):
        args = [a for a in annotation.__args__ if a is not type(None)]
        if args:
            return args[0], True
    return annotation, False


def _parse_env_value(value: str, annotation: Any) -> Any:
    """Parse an environment variable value to the target type."""
    if annotation is None:
        return value

    annotation, _ = _unwrap_optional(annotation)

    if annotation is bool:
        return value.lower() in ("true", "1", "yes", "on")
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        parser = _create_enum_parser(annotation)
        return parser(value)
    if _is_list_type(annotation):
        element_type = _get_list_element_type(annotation)
        if not value:
            return []
        values = [v.strip() for v in value.split(",")]
        return [_parse_env_value(v, element_type) for v in values]

    return value


def _is_list_type(annotation: Any) -> bool:
    """Check if the annotation is a List type."""
    return get_origin(annotation) is list


def _get_list_element_type(annotation: Any) -> Type:
    """Get the element type from a List annotation."""
    args = get_args(annotation)
    return args[0] if args else str


def _create_enum_parser(
    enum_class: Type[Enum],
) -> Callable[[str], Enum]:
    """Create a parser for enum types handling string and int values."""

    def parse_enum(value: str) -> Enum:
        for member in enum_class:
            if member.name.lower() == value.lower():
                return member
        for member in enum_class:
            if str(member.value).lower() == value.lower():
                return member
        try:
            int_value = int(value)
            for member in enum_class:
                if member.value == int_value:
                    return member
        except ValueError:
            pass

        valid = [f"{m.name} ({m.value})" for m in enum_class]
        raise argparse.ArgumentTypeError(
            f"invalid {enum_class.__name__} value: '{value}'. "
            f"Valid choices: {', '.join(valid)}"
        )

    return parse_enum


def _build_positional_kwargs(
    field_info: Any, field_value: "KliamkaArg"
) -> dict[str, Any]:
    """Build argparse kwargs for a positional argument."""
    help_text = field_value.help_text
    if field_value.env:
        help_text += f" [env: {field_value.env}]"

    kwargs: dict[str, Any] = {"help": help_text}
    annotation = field_info.annotation
    annotation, is_optional = _unwrap_optional(annotation)

    if _is_list_type(annotation):
        element_type = _get_list_element_type(annotation)
        kwargs["nargs"] = "*"
        kwargs["default"] = (
            field_value.default if field_value.default is not None else []
        )
        if isinstance(element_type, type) and issubclass(element_type, Enum):
            kwargs["type"] = _create_enum_parser(element_type)
        else:
            kwargs["type"] = element_type if element_type is not None else str
    else:
        if is_optional or field_value.default is not None:
            kwargs["nargs"] = "?"
            kwargs["default"] = field_value.default

        if (
            annotation is not None
            and isinstance(annotation, type)
            and issubclass(annotation, Enum)
        ):
            kwargs["type"] = _create_enum_parser(annotation)
            choices = [f"{m.name}({m.value})" for m in annotation]
            kwargs["metavar"] = "{" + ",".join(choices) + "}"
        else:
            kwargs["type"] = annotation if annotation is not None else str

    return kwargs


def _build_optional_kwargs(
    field_info: Any, field_value: "KliamkaArg"
) -> dict[str, Any]:
    """Build argparse kwargs for an optional (flag) argument."""
    help_text = field_value.help_text
    if field_value.env:
        help_text += f" [env: {field_value.env}]"

    kwargs: dict[str, Any] = {
        "help": help_text,
        "default": field_value.default,
    }

    if _is_bool_annotation(field_info.annotation):
        kwargs["action"] = "store_true"
        kwargs["default"] = (
            field_value.default if field_value.default is not None else False
        )
    else:
        annotation, _ = _unwrap_optional(field_info.annotation)

        if _is_list_type(annotation):
            element_type = _get_list_element_type(annotation)
            kwargs["nargs"] = "*"
            kwargs["default"] = (
                field_value.default if field_value.default is not None else []
            )
            if isinstance(element_type, type) and issubclass(element_type, Enum):
                kwargs["type"] = _create_enum_parser(element_type)
            else:
                kwargs["type"] = element_type if element_type is not None else str
        elif (
            annotation is not None
            and isinstance(annotation, type)
            and issubclass(annotation, Enum)
        ):
            kwargs["type"] = _create_enum_parser(annotation)
            choices = [f"{m.name}({m.value})" for m in annotation]
            kwargs["metavar"] = "{" + ",".join(choices) + "}"
        else:
            kwargs["type"] = annotation if annotation is not None else str

    return kwargs


def _get_flag_names(field_value: "KliamkaArg") -> list[str]:
    """Get all flag names (long + short) for an argument."""
    flags = [field_value.flag]
    if field_value.short:
        flags.insert(0, field_value.short)
    return flags


def _populate_parser(
    parser: argparse.ArgumentParser,
    arg_class: Type["KliamkaArgClass"],
) -> None:
    """Populate an ArgumentParser with arguments from a KliamkaArgClass."""
    positional_args: list[tuple[str, Any, "KliamkaArg"]] = []
    optional_args: list[tuple[str, Any, "KliamkaArg"]] = []
    # group_name -> list of (field_name, field_info, field_value)
    exclusive_groups: dict[str, list[tuple[str, Any, "KliamkaArg"]]] = {}

    for field_name, field_info in arg_class.model_fields.items():
        if not isinstance(field_info.default, KliamkaArg):
            continue
        field_value = field_info.default
        is_positional = field_value.positional or not field_value.flag.startswith("-")

        if field_value.mutually_exclusive:
            group_name = field_value.mutually_exclusive
            if group_name not in exclusive_groups:
                exclusive_groups[group_name] = []
            exclusive_groups[group_name].append((field_name, field_info, field_value))
        elif is_positional:
            positional_args.append((field_name, field_info, field_value))
        else:
            optional_args.append((field_name, field_info, field_value))

    for _field_name, field_info, field_value in positional_args:
        kwargs = _build_positional_kwargs(field_info, field_value)
        parser.add_argument(field_value.flag, **kwargs)

    for _field_name, field_info, field_value in optional_args:
        kwargs = _build_optional_kwargs(field_info, field_value)
        flags = _get_flag_names(field_value)
        parser.add_argument(*flags, **kwargs)

    for _group_name, members in exclusive_groups.items():
        group = parser.add_mutually_exclusive_group()
        for _field_name, field_info, field_value in members:
            kwargs = _build_optional_kwargs(field_info, field_value)
            flags = _get_flag_names(field_value)
            group.add_argument(*flags, **kwargs)


class KliamkaArg:
    """Descriptor for CLI arguments.

    Args:
        flag: The flag name (e.g. "--verbose" or "filename").
        help_text: Help text for the argument.
        default: Default value when not provided.
        positional: Whether this is a positional argument.
        env: Environment variable name for fallback.
        short: Short flag alias (e.g. "-v").
        mutually_exclusive: Group name for mutual exclusion.
    """

    def __init__(
        self,
        flag: str,
        help_text: str = "",
        default: Any = None,
        positional: bool = False,
        env: Optional[str] = None,
        short: Optional[str] = None,
        mutually_exclusive: Optional[str] = None,
    ) -> None:
        self.flag = flag
        self.help_text = help_text
        self.default = default
        self.positional = positional
        self.env = env
        self.short = short
        self.mutually_exclusive = mutually_exclusive
        self.name = ""

    def __set_name__(self, owner: Type, name: str) -> None:
        self.name = name


class ParserMeta:
    """Container for parser customization options.

    Attributes:
        prog: Program name for help text.
        usage: Custom usage string.
        epilog: Text after the help message.
        version: Version string for --version flag.
    """

    def __init__(
        self,
        prog: Optional[str] = None,
        usage: Optional[str] = None,
        epilog: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version


class KliamkaArgClass(BaseModel):
    """Base class for CLI argument definitions.

    Subclass this with KliamkaArg fields to define your CLI.
    Supports Pydantic validators via @model_validator.

    Set ``parser_meta`` class variable for customization::

        class MyArgs(KliamkaArgClass):
            parser_meta = ParserMeta(
                prog="myapp",
                version="myapp 1.0",
                epilog="See docs for more info.",
            )
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "ignored_types": (ParserMeta,),
    }

    @classmethod
    def _get_parser_meta(cls) -> ParserMeta:
        """Get parser meta from class hierarchy."""
        for klass in cls.__mro__:
            if "parser_meta" in klass.__dict__:
                meta = klass.__dict__["parser_meta"]
                if isinstance(meta, ParserMeta):
                    return meta
        return ParserMeta()

    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """Create an ArgumentParser from the class definition."""
        meta = cls._get_parser_meta()
        parser_kwargs: dict[str, Any] = {
            "description": cls.__doc__ or "",
        }

        if meta.prog is not None:
            parser_kwargs["prog"] = meta.prog
        if meta.usage is not None:
            parser_kwargs["usage"] = meta.usage
        if meta.epilog is not None:
            parser_kwargs["epilog"] = meta.epilog

        parser = argparse.ArgumentParser(**parser_kwargs)

        if meta.version is not None:
            parser.add_argument(
                "--version",
                action="version",
                version=meta.version,
            )

        _populate_parser(parser, cls)
        return parser

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "KliamkaArgClass":
        """Create instance from parsed arguments."""
        kwargs: dict[str, Any] = {}
        for field_name, field_info in cls.model_fields.items():
            if not isinstance(field_info.default, KliamkaArg):
                kwargs[field_name] = getattr(args, field_name, field_info.default)
                continue

            field_value = field_info.default
            is_positional = field_value.positional or not field_value.flag.startswith(
                "-"
            )
            if is_positional:
                arg_name = field_value.flag.replace("-", "_")
            else:
                arg_name = field_value.flag.lstrip("-").replace("-", "_")

            cli_value = getattr(args, arg_name, None)
            annotation = field_info.annotation

            cli_provided = _was_cli_provided(cli_value, annotation, field_value)

            # Priority: CLI > ENV > default
            if cli_provided:
                kwargs[field_name] = cli_value
            elif field_value.env and os.environ.get(field_value.env):
                env_val = os.environ[field_value.env]
                kwargs[field_name] = _parse_env_value(env_val, annotation)
            else:
                kwargs[field_name] = (
                    cli_value if cli_value is not None else field_value.default
                )

        return cls(**kwargs)


def _was_cli_provided(cli_value: Any, annotation: Any, field_value: KliamkaArg) -> bool:
    """Determine if a CLI value was explicitly provided."""
    if _is_bool_annotation(annotation):
        return cli_value is True

    is_list = _is_list_type(annotation) or (
        annotation is not None
        and hasattr(annotation, "__origin__")
        and getattr(annotation, "__origin__", None) is Union
        and any(
            _is_list_type(a)
            for a in getattr(annotation, "__args__", ())
            if a is not type(None)
        )
    )

    if is_list:
        return bool(cli_value)

    return cli_value is not None and cli_value != field_value.default


def kliamka_cli(
    arg_class: Type[KliamkaArgClass],
    argv: Optional[Sequence[str]] = None,
) -> Callable[[F], F]:
    """Decorator that injects CLI arguments as the first parameter.

    Args:
        arg_class: KliamkaArgClass subclass defining CLI arguments.
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Decorated function with CLI argument injection.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            parser = arg_class.create_parser()
            parsed_args = parser.parse_args(argv)
            instance = arg_class.from_args(parsed_args)
            return func(instance, *args, **kwargs)

        wrapper._kliamka_func = func  # type: ignore[attr-defined]
        wrapper._kliamka_arg_class = arg_class  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def kliamka_subcommands(
    main_class: Type[KliamkaArgClass],
    subcommands: dict[str, Type[KliamkaArgClass]],
    argv: Optional[Sequence[str]] = None,
) -> Callable[[F], F]:
    """Decorator for CLI applications with subcommands.

    Args:
        main_class: KliamkaArgClass for global CLI arguments.
        subcommands: Dict mapping command names to arg classes.
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Decorated function with subcommand support.

    Example:
        @kliamka_subcommands(MainArgs, {"add": AddArgs})
        def main(args: MainArgs, command: str, cmd_args) -> None:
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            meta = main_class._get_parser_meta()
            parser_kwargs: dict[str, Any] = {
                "description": main_class.__doc__ or "",
            }
            if meta.prog is not None:
                parser_kwargs["prog"] = meta.prog
            if meta.epilog is not None:
                parser_kwargs["epilog"] = meta.epilog

            parser = argparse.ArgumentParser(**parser_kwargs)

            if meta.version is not None:
                parser.add_argument(
                    "--version",
                    action="version",
                    version=meta.version,
                )

            _populate_parser(parser, main_class)

            subparsers = parser.add_subparsers(dest="_command", required=True)
            for cmd_name, cmd_class in subcommands.items():
                sub_parser = subparsers.add_parser(
                    cmd_name,
                    help=cmd_class.__doc__ or "",
                    description=cmd_class.__doc__ or "",
                )
                _populate_parser(sub_parser, cmd_class)

            parsed_args = parser.parse_args(argv)
            command = parsed_args._command

            main_instance = main_class.from_args(parsed_args)
            cmd_class = subcommands[command]
            cmd_instance = cmd_class.from_args(parsed_args)

            return func(main_instance, command, cmd_instance, *args, **kwargs)

        wrapper._kliamka_func = func  # type: ignore[attr-defined]
        wrapper._kliamka_main_class = main_class  # type: ignore[attr-defined]
        wrapper._kliamka_subcommands = subcommands  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
