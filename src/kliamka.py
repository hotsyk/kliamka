"""Kliamka - Small Python CLI library."""

import argparse
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar, Union
from pydantic import BaseModel

__version__ = "0.2.0"
__author__ = "Volodymyr Hotsyk"
__email__ = "git@hotsyk.com"


class KliamkaError(Exception):
    """Base exception for kliamka library."""

    pass


F = TypeVar("F", bound=Callable[..., Any])


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

    def __init__(self, flag: str, help_text: str = "", default: Any = None) -> None:
        self.flag = flag
        self.help_text = help_text
        self.default = default
        self.name = ""

    def __set_name__(self, owner: Type, name: str) -> None:
        self.name = name


class KliamkaArgClass(BaseModel):
    """Base class for CLI argument definitions."""

    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """Create an ArgumentParser from the class definition."""
        parser = argparse.ArgumentParser(description=cls.__doc__ or "")

        for field_name, field_info in cls.model_fields.items():
            if isinstance(field_info.default, KliamkaArg):
                field_value = field_info.default
                kwargs = {"help": field_value.help_text, "default": field_value.default}
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
                        args = [
                            arg for arg in annotation.__args__ if arg is not type(None)
                        ]
                        if args:
                            annotation = args[0]

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

        return parser

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        """Create instance from parsed arguments."""
        kwargs = {}
        for field_name, field_info in cls.model_fields.items():
            if isinstance(field_info.default, KliamkaArg):
                field_value = field_info.default
                arg_name = field_value.flag.lstrip("-").replace("-", "_")
                kwargs[field_name] = getattr(args, arg_name, field_value.default)
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
