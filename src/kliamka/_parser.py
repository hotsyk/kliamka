"""Internal argparse population from KliamkaArgClass definitions."""

from __future__ import annotations

import argparse
from enum import Enum
from functools import cache
from typing import TYPE_CHECKING, Any, Type

from ._converters import _CONVERTERS, _resolve_type_converter
from ._helpers import (
    _UNSET,
    _get_list_element_type,
    _is_bool_annotation,
    _is_list_type,
    _unwrap_optional,
)

if TYPE_CHECKING:
    from ._core import KliamkaArg, KliamkaArgClass


def _build_help_text(field_value: "KliamkaArg") -> str:
    """Build help text, including an environment fallback hint."""
    help_text = field_value.help_text
    if field_value.env:
        help_text += f" [env: {field_value.env}]"
    return help_text


def _build_type_kwargs(
    annotation: Any,
    field_value: "KliamkaArg",
) -> tuple[dict[str, Any], bool]:
    """Build shared argparse type kwargs for positional and optional args."""
    unwrapped, is_optional = _unwrap_optional(annotation)
    resolved = _resolve_type_converter(unwrapped, field_value)
    kwargs: dict[str, Any] = {}

    if _is_list_type(unwrapped):
        element_type = _get_list_element_type(unwrapped)
        kwargs["nargs"] = "*"
        kwargs["type"] = resolved or element_type or str
    elif (
        unwrapped is not None
        and isinstance(unwrapped, type)
        and issubclass(unwrapped, Enum)
    ):
        kwargs["type"] = resolved
        choices = [f"{member.name}({member.value})" for member in unwrapped]
        kwargs["metavar"] = "{" + ",".join(choices) + "}"
    elif resolved is not None:
        kwargs["type"] = resolved
    else:
        kwargs["type"] = unwrapped if unwrapped is not None else str

    return kwargs, is_optional


def _build_positional_kwargs(
    field_info: Any, field_value: "KliamkaArg"
) -> dict[str, Any]:
    """Build argparse kwargs for a positional argument."""
    kwargs, is_optional = _build_type_kwargs(field_info.annotation, field_value)
    kwargs["help"] = _build_help_text(field_value)

    if kwargs.get("nargs") == "*":
        kwargs["default"] = _UNSET
    elif is_optional or field_value.default is not None:
        kwargs["nargs"] = "?"
        kwargs["default"] = _UNSET

    return kwargs


def _build_optional_kwargs(
    field_info: Any, field_value: "KliamkaArg"
) -> dict[str, Any]:
    """Build argparse kwargs for an optional (flag) argument."""
    kwargs: dict[str, Any] = {
        "help": _build_help_text(field_value),
        "default": _UNSET,
    }

    if _is_bool_annotation(field_info.annotation):
        _unwrap_optional(field_info.annotation)
        kwargs["action"] = "store_true"
    else:
        type_kwargs, _ = _build_type_kwargs(field_info.annotation, field_value)
        kwargs.update(type_kwargs)

    return kwargs


def _get_flag_names(field_value: "KliamkaArg") -> list[str]:
    """Get all flag names (long + short) for an argument."""
    flags = [field_value.flag]
    if field_value.short:
        flags.insert(0, field_value.short)
    return flags


_ArgumentRecipe = tuple[tuple[str, ...], dict[str, Any]]
_ParserPlan = tuple[
    tuple[_ArgumentRecipe, ...],
    tuple[_ArgumentRecipe, ...],
    tuple[tuple[str, tuple[_ArgumentRecipe, ...]], ...],
]


def _parser_plan_signature(arg_class: Type["KliamkaArgClass"]) -> tuple[Any, ...]:
    """Describe inputs that affect the reusable argument-construction plan."""
    from ._core import KliamkaArg  # local import breaks the _core<->_parser cycle

    fields = []
    for field_name, field_info in arg_class.model_fields.items():
        field_value = field_info.default
        if not isinstance(field_value, KliamkaArg):
            continue
        fields.append(
            (
                field_name,
                id(field_info.annotation),
                field_value.flag,
                field_value.help_text,
                field_value.default is not None,
                field_value.positional,
                field_value.env,
                field_value.short,
                field_value.mutually_exclusive,
                id(field_value.converter),
                field_value.name,
            )
        )
    converters = tuple((id(tp), id(converter)) for tp, converter in _CONVERTERS.items())
    return tuple(fields), converters


@cache
def _build_parser_plan(
    arg_class: Type["KliamkaArgClass"],
    _signature: tuple[Any, ...],
) -> _ParserPlan:
    """Compile immutable model metadata into reusable argparse recipes."""
    from ._core import KliamkaArg  # local import breaks the _core<->_parser cycle

    positional_args: list[_ArgumentRecipe] = []
    optional_args: list[_ArgumentRecipe] = []
    exclusive_groups: dict[str, list[_ArgumentRecipe]] = {}

    for field_name, field_info in arg_class.model_fields.items():
        field_value = field_info.default
        if not isinstance(field_value, KliamkaArg):
            continue

        if field_value.mutually_exclusive:
            kwargs = _build_optional_kwargs(field_info, field_value)
            kwargs["dest"] = field_value.name or field_name
            recipe = (tuple(_get_flag_names(field_value)), kwargs)
            exclusive_groups.setdefault(field_value.mutually_exclusive, []).append(
                recipe
            )
        elif field_value.positional or not field_value.flag.startswith("-"):
            kwargs = _build_positional_kwargs(field_info, field_value)
            dest = field_value.name or field_name
            if dest != field_value.flag:
                kwargs.setdefault("metavar", field_value.flag)
            positional_args.append(((dest,), kwargs))
        else:
            kwargs = _build_optional_kwargs(field_info, field_value)
            kwargs["dest"] = field_value.name or field_name
            optional_args.append((tuple(_get_flag_names(field_value)), kwargs))

    return (
        tuple(positional_args),
        tuple(optional_args),
        tuple((name, tuple(recipes)) for name, recipes in exclusive_groups.items()),
    )


def _populate_parser(
    parser: argparse.ArgumentParser,
    arg_class: Type["KliamkaArgClass"],
) -> None:
    """Populate an ArgumentParser with arguments from a KliamkaArgClass."""
    try:
        positional_args, optional_args, exclusive_groups = _build_parser_plan(
            arg_class, _parser_plan_signature(arg_class)
        )

        for flags, kwargs in positional_args:
            parser.add_argument(*flags, **kwargs)

        for flags, kwargs in optional_args:
            parser.add_argument(*flags, **kwargs)

        for _group_name, members in exclusive_groups:
            group = parser.add_mutually_exclusive_group()
            for flags, kwargs in members:
                group.add_argument(*flags, **kwargs)
    except ValueError as exc:
        from ._core import KliamkaError

        raise KliamkaError(str(exc)) from exc
