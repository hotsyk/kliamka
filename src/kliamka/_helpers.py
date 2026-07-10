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
    """Unwrap ``Optional[T]`` and reject unsupported wider unions.

    Raises:
        ValueError: If ``annotation`` is a union other than ``T | None``.
    """
    if annotation is None or not _is_union(annotation):
        return annotation, False

    members = get_args(annotation)
    non_none = [member for member in members if member is not type(None)]
    has_none = any(member is type(None) for member in members)
    if has_none and len(non_none) == 1:
        return non_none[0], True

    raise ValueError(
        f"unsupported union annotation {annotation!r}; only Optional[T] / T | None "
        "unions are supported"
    )


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
