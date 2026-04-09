import argparse
from enum import Enum
from typing import Any, Callable, Type, Union, get_args, get_origin


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
