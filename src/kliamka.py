"""Kliamka - Small Python CLI library."""

import argparse
import os
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar, Union, get_origin, get_args
from pydantic import BaseModel

__version__ = "0.2.0"
__author__ = "Volodymyr Hotsyk"
__email__ = "git@hotsyk.com"


class KliamkaError(Exception):
    """Base exception for kliamka library."""

    pass


F = TypeVar("F", bound=Callable[..., Any])


def _parse_env_value(value: str, annotation: Any) -> Any:
    """Parse an environment variable value to the target type."""
    if annotation is None:
        return value

    # Handle Optional types
    if hasattr(annotation, "__origin__") and annotation.__origin__ is Union:
        args = [arg for arg in annotation.__args__ if arg is not type(None)]
        if args:
            annotation = args[0]

    # Handle bool
    if annotation is bool:
        return value.lower() in ("true", "1", "yes", "on")

    # Handle int
    if annotation is int:
        return int(value)

    # Handle float
    if annotation is float:
        return float(value)

    # Handle enum
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        parser = _create_enum_parser(annotation)
        return parser(value)

    # Handle list (split by comma)
    if _is_list_type(annotation):
        element_type = _get_list_element_type(annotation)
        if not value:
            return []
        values = [v.strip() for v in value.split(",")]
        return [_parse_env_value(v, element_type) for v in values]

    # Default to string
    return value


def _is_list_type(annotation: Any) -> bool:
    """Check if the annotation is a List type."""
    origin = get_origin(annotation)
    return origin is list


def _get_list_element_type(annotation: Any) -> Type:
    """Get the element type from a List annotation."""
    args = get_args(annotation)
    return args[0] if args else str


def _create_enum_parser(enum_class: Type[Enum]) -> Callable[[str], Enum]:
    """Create a parser function for enum types that handles both string and integer values."""

    def parse_enum(value: str) -> Enum:
        for enum_member in enum_class:
            if enum_member.name.lower() == value.lower():
                return enum_member

        for enum_member in enum_class:
            if str(enum_member.value).lower() == value.lower():
                return enum_member

        try:
            int_value = int(value)
            for enum_member in enum_class:
                if enum_member.value == int_value:
                    return enum_member
        except ValueError:
            pass

        valid_values = []
        for enum_member in enum_class:
            valid_values.append(f"{enum_member.name} ({enum_member.value})")

        raise argparse.ArgumentTypeError(
            f"invalid {enum_class.__name__} value: '{value}'. "
            f"Valid choices: {', '.join(valid_values)}"
        )

    return parse_enum


class KliamkaArg:
    """Descriptor for CLI arguments."""

    def __init__(
        self,
        flag: str,
        help_text: str = "",
        default: Any = None,
        positional: bool = False,
        env: Optional[str] = None,
    ) -> None:
        self.flag = flag
        self.help_text = help_text
        self.default = default
        self.positional = positional
        self.env = env
        self.name = ""

    def __set_name__(self, owner: Type, name: str) -> None:
        self.name = name


class KliamkaArgClass(BaseModel):
    """Base class for CLI argument definitions."""

    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """Create an ArgumentParser from the class definition."""
        parser = argparse.ArgumentParser(description=cls.__doc__ or "")

        # Separate positional and optional arguments
        positional_args = []
        optional_args = []

        for field_name, field_info in cls.model_fields.items():
            if isinstance(field_info.default, KliamkaArg):
                field_value = field_info.default
                is_positional = (
                    field_value.positional or not field_value.flag.startswith("-")
                )
                if is_positional:
                    positional_args.append((field_name, field_info, field_value))
                else:
                    optional_args.append((field_name, field_info, field_value))

        # Add positional arguments first
        for field_name, field_info, field_value in positional_args:
            help_text = field_value.help_text
            if field_value.env:
                help_text += f" [env: {field_value.env}]"
            kwargs: dict[str, Any] = {"help": help_text}
            annotation = field_info.annotation

            # Handle Optional types
            is_optional_type = False
            if (
                annotation is not None
                and hasattr(annotation, "__origin__")
                and annotation.__origin__ is Union
            ):
                args = [arg for arg in annotation.__args__ if arg is not type(None)]
                if args:
                    annotation = args[0]
                    is_optional_type = True

            # Handle List types
            is_list = _is_list_type(annotation)
            if is_list:
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
                # For optional positional arguments, use nargs='?'
                if is_optional_type or field_value.default is not None:
                    kwargs["nargs"] = "?"
                    kwargs["default"] = field_value.default

                if (
                    annotation is not None
                    and isinstance(annotation, type)
                    and issubclass(annotation, Enum)
                ):
                    kwargs["type"] = _create_enum_parser(annotation)
                    choices = []
                    for enum_member in annotation:
                        choices.append(f"{enum_member.name}({enum_member.value})")
                    kwargs["metavar"] = "{" + ",".join(choices) + "}"
                else:
                    kwargs["type"] = annotation if annotation is not None else str

            parser.add_argument(field_value.flag, **kwargs)

        # Add optional arguments
        for field_name, field_info, field_value in optional_args:
            help_text = field_value.help_text
            if field_value.env:
                help_text += f" [env: {field_value.env}]"
            kwargs = {"help": help_text, "default": field_value.default}
            if (
                field_info.annotation in (bool, Optional[bool])
                or str(field_info.annotation) == "typing.Union[bool, NoneType]"
            ):
                kwargs["action"] = "store_true"
                if field_value.default is not None:
                    kwargs["default"] = field_value.default
                else:
                    kwargs["default"] = False
            else:
                annotation = field_info.annotation
                if (
                    annotation is not None
                    and hasattr(annotation, "__origin__")
                    and annotation.__origin__ is Union
                ):
                    args = [arg for arg in annotation.__args__ if arg is not type(None)]
                    if args:
                        annotation = args[0]

                # Handle List types
                if _is_list_type(annotation):
                    element_type = _get_list_element_type(annotation)
                    kwargs["nargs"] = "*"
                    kwargs["default"] = (
                        field_value.default if field_value.default is not None else []
                    )

                    if isinstance(element_type, type) and issubclass(
                        element_type, Enum
                    ):
                        kwargs["type"] = _create_enum_parser(element_type)
                    else:
                        kwargs["type"] = (
                            element_type if element_type is not None else str
                        )
                elif (
                    annotation is not None
                    and isinstance(annotation, type)
                    and issubclass(annotation, Enum)
                ):
                    kwargs["type"] = _create_enum_parser(annotation)
                    choices = []
                    for enum_member in annotation:
                        choices.append(f"{enum_member.name}({enum_member.value})")
                    kwargs["metavar"] = "{" + ",".join(choices) + "}"
                else:
                    kwargs["type"] = annotation if annotation is not None else str

            parser.add_argument(field_value.flag, **kwargs)

        return parser

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        """Create instance from parsed arguments."""
        kwargs = {}
        for field_name, field_info in cls.model_fields.items():
            if isinstance(field_info.default, KliamkaArg):
                field_value = field_info.default
                is_positional = (
                    field_value.positional or not field_value.flag.startswith("-")
                )
                if is_positional:
                    # Positional args use the flag name directly
                    arg_name = field_value.flag.replace("-", "_")
                else:
                    # Optional args strip leading dashes
                    arg_name = field_value.flag.lstrip("-").replace("-", "_")

                cli_value = getattr(args, arg_name, None)
                annotation = field_info.annotation

                # Determine if CLI value was explicitly provided
                # For bools with store_true: True means provided, False means not
                # For lists: non-empty means provided
                # For others: not None and not equal to default means provided
                is_bool_type = (
                    annotation in (bool, Optional[bool])
                    or str(annotation) == "typing.Union[bool, NoneType]"
                )
                is_list_type = _is_list_type(annotation) or (
                    annotation is not None
                    and hasattr(annotation, "__origin__")
                    and getattr(annotation, "__origin__", None) is Union
                    and any(
                        _is_list_type(a)
                        for a in getattr(annotation, "__args__", ())
                        if a is not type(None)
                    )
                )

                cli_explicitly_provided = False
                if is_bool_type and cli_value is True:
                    # Bool flag was provided on CLI
                    cli_explicitly_provided = True
                elif is_list_type and cli_value and cli_value != []:
                    # List was provided on CLI
                    cli_explicitly_provided = True
                elif not is_bool_type and not is_list_type:
                    # For other types, check if value differs from default
                    # If default is None and cli_value is also None, not provided
                    # If default is set and cli_value differs, it was provided
                    if cli_value is not None and cli_value != field_value.default:
                        cli_explicitly_provided = True

                # Priority: CLI > ENV > default
                if cli_explicitly_provided:
                    kwargs[field_name] = cli_value
                elif field_value.env and os.environ.get(field_value.env):
                    # Environment variable is set
                    env_val = os.environ.get(field_value.env)
                    assert env_val is not None  # Guaranteed by the condition above
                    kwargs[field_name] = _parse_env_value(env_val, annotation)
                else:
                    # Use CLI value (might be default) or fall back to default
                    kwargs[field_name] = (
                        cli_value if cli_value is not None else field_value.default
                    )
            else:
                kwargs[field_name] = getattr(args, field_name, field_info.default)

        return cls(**kwargs)


def kliamka_cli(arg_class: Type[KliamkaArgClass]) -> Callable[[F], F]:
    """Decorator that injects CLI arguments as the first parameter.

    Args:
        arg_class: KliamkaArgClass subclass defining CLI arguments

    Returns:
        Decorated function with CLI argument injection
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            parser = arg_class.create_parser()
            parsed_args = parser.parse_args()
            kliamka_instance = arg_class.from_args(parsed_args)
            return func(kliamka_instance, *args, **kwargs)

        wrapper._kliamka_func = func  # type: ignore[attr-defined]
        wrapper._kliamka_arg_class = arg_class  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def _populate_parser(
    parser: argparse.ArgumentParser, arg_class: Type[KliamkaArgClass]
) -> None:
    """Populate an ArgumentParser with arguments from a KliamkaArgClass.

    This is a helper function that extracts the parser population logic
    to be reused for subcommands.
    """
    # Separate positional and optional arguments
    positional_args = []
    optional_args = []

    for field_name, field_info in arg_class.model_fields.items():
        if isinstance(field_info.default, KliamkaArg):
            field_value = field_info.default
            is_positional = field_value.positional or not field_value.flag.startswith(
                "-"
            )
            if is_positional:
                positional_args.append((field_name, field_info, field_value))
            else:
                optional_args.append((field_name, field_info, field_value))

    # Add positional arguments first
    for field_name, field_info, field_value in positional_args:
        help_text = field_value.help_text
        if field_value.env:
            help_text += f" [env: {field_value.env}]"
        kwargs: dict[str, Any] = {"help": help_text}
        annotation = field_info.annotation

        # Handle Optional types
        is_optional_type = False
        if (
            annotation is not None
            and hasattr(annotation, "__origin__")
            and annotation.__origin__ is Union
        ):
            args = [arg for arg in annotation.__args__ if arg is not type(None)]
            if args:
                annotation = args[0]
                is_optional_type = True

        # Handle List types
        is_list = _is_list_type(annotation)
        if is_list:
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
            # For optional positional arguments, use nargs='?'
            if is_optional_type or field_value.default is not None:
                kwargs["nargs"] = "?"
                kwargs["default"] = field_value.default

            if (
                annotation is not None
                and isinstance(annotation, type)
                and issubclass(annotation, Enum)
            ):
                kwargs["type"] = _create_enum_parser(annotation)
                choices = []
                for enum_member in annotation:
                    choices.append(f"{enum_member.name}({enum_member.value})")
                kwargs["metavar"] = "{" + ",".join(choices) + "}"
            else:
                kwargs["type"] = annotation if annotation is not None else str

        parser.add_argument(field_value.flag, **kwargs)

    # Add optional arguments
    for field_name, field_info, field_value in optional_args:
        help_text = field_value.help_text
        if field_value.env:
            help_text += f" [env: {field_value.env}]"
        kwargs = {"help": help_text, "default": field_value.default}
        if (
            field_info.annotation in (bool, Optional[bool])
            or str(field_info.annotation) == "typing.Union[bool, NoneType]"
        ):
            kwargs["action"] = "store_true"
            if field_value.default is not None:
                kwargs["default"] = field_value.default
            else:
                kwargs["default"] = False
        else:
            annotation = field_info.annotation
            if (
                annotation is not None
                and hasattr(annotation, "__origin__")
                and annotation.__origin__ is Union
            ):
                args = [arg for arg in annotation.__args__ if arg is not type(None)]
                if args:
                    annotation = args[0]

            # Handle List types
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
                choices = []
                for enum_member in annotation:
                    choices.append(f"{enum_member.name}({enum_member.value})")
                kwargs["metavar"] = "{" + ",".join(choices) + "}"
            else:
                kwargs["type"] = annotation if annotation is not None else str

        parser.add_argument(field_value.flag, **kwargs)


def kliamka_subcommands(
    main_class: Type[KliamkaArgClass],
    subcommands: dict[str, Type[KliamkaArgClass]],
) -> Callable[[F], F]:
    """Decorator for CLI applications with subcommands.

    Args:
        main_class: KliamkaArgClass subclass defining global CLI arguments
        subcommands: Dictionary mapping command names to KliamkaArgClass subclasses

    Returns:
        Decorated function with subcommand support

    Example:
        class MainArgs(KliamkaArgClass):
            verbose: Optional[bool] = KliamkaArg("--verbose", "Verbose output")

        class AddArgs(KliamkaArgClass):
            name: str = KliamkaArg("name", "Item name", positional=True)

        @kliamka_subcommands(MainArgs, {"add": AddArgs})
        def main(args: MainArgs, command: str, cmd_args: AddArgs) -> None:
            if command == "add":
                print(f"Adding {cmd_args.name}")
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create main parser with global arguments
            parser = argparse.ArgumentParser(description=main_class.__doc__ or "")
            _populate_parser(parser, main_class)

            # Add subparsers
            subparsers = parser.add_subparsers(dest="_command", required=True)

            for cmd_name, cmd_class in subcommands.items():
                sub_parser = subparsers.add_parser(
                    cmd_name,
                    help=cmd_class.__doc__ or "",
                    description=cmd_class.__doc__ or "",
                )
                _populate_parser(sub_parser, cmd_class)

            # Parse arguments
            parsed_args = parser.parse_args()
            command = parsed_args._command

            # Create instances
            main_instance = main_class.from_args(parsed_args)
            cmd_class = subcommands[command]
            cmd_instance = cmd_class.from_args(parsed_args)

            return func(main_instance, command, cmd_instance, *args, **kwargs)

        wrapper._kliamka_func = func  # type: ignore[attr-defined]
        wrapper._kliamka_main_class = main_class  # type: ignore[attr-defined]
        wrapper._kliamka_subcommands = subcommands  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
