import argparse
import types
from enum import Enum
from typing import Any, Callable, Type, Union, get_args, get_origin


class _UnsetType:
    """Sentinel default distinguishing "not given on the CLI" from any real value."""

    def __repr__(self) -> str:
        return "<kliamka.UNSET>"

    def __bool__(self) -> bool:
        return False


_UNSET = _UnsetType()


def _is_union(annotation: Any) -> bool:
    """Check if annotation is a Union, either typing.Union or PEP 604 (X | Y)."""
    origin = get_origin(annotation)
    return origin is Union or origin is types.UnionType


def _is_bool_annotation(annotation: Any) -> bool:
    """Check if annotation represents a bool type."""
    if annotation is bool:
        return True
    if _is_union(annotation):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        return len(non_none) == 1 and non_none[0] is bool
    return False


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Unwrap Optional[T] to (T, True) or return (annotation, False)."""
    if annotation is not None and _is_union(annotation):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if args:
            return args[0], True
    return annotation, False


def _is_list_type(annotation: Any) -> bool:
    """Check if the annotation is a List type."""
    return get_origin(annotation) is list


def _get_list_element_type(annotation: Any) -> Type:
    """Get the element type from a List annotation."""
    args = get_args(annotation)
    return args[0] if args else str


def _get_arg_dest(flag: str, positional: bool = False) -> str:
    """Compute the argparse namespace attribute name for an argument.

    argparse normalizes hyphens to underscores only for option flags, so
    positional names are normalized here and passed as the argument name.
    """
    if positional or not flag.startswith("-"):
        return flag.replace("-", "_")
    return flag.lstrip("-").replace("-", "_")


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
