"""Internal argparse population from KliamkaArgClass definitions."""

from __future__ import annotations

import argparse
import os
import sys
from enum import Enum
from functools import cache
from typing import TYPE_CHECKING, Any, Type

from ._converters import _resolve_type_converter
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
        converter = resolved or element_type
        if converter is not None and converter is not str:
            kwargs["type"] = converter
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
    tuple[argparse.Action, ...],
    tuple[tuple[str, tuple[argparse.Action, ...]], ...],
]


@cache
def _build_parser_plan(
    arg_class: Type["KliamkaArgClass"],
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

    template_parser = argparse.ArgumentParser(add_help=False)
    actions = tuple(
        template_parser.add_argument(*flags, **kwargs)
        for flags, kwargs in positional_args + optional_args
    )
    group_actions = []
    for name, recipes in exclusive_groups.items():
        group = template_parser.add_mutually_exclusive_group()
        group_actions.append(
            (
                name,
                tuple(
                    group.add_argument(*flags, **kwargs) for flags, kwargs in recipes
                ),
            )
        )
    return actions, tuple(group_actions)


def _clear_parser_plan_cache() -> None:
    """Invalidate compiled plans after argument schema or converter changes."""
    _build_parser_plan.cache_clear()


def _copy_action(action: argparse.Action) -> argparse.Action:
    """Reconstruct an Action using the same state update as ``copy.copy``."""
    clone = object.__new__(type(action))
    clone.__dict__.update(action.__dict__)
    return clone


@cache
def _argument_parser_template() -> argparse.ArgumentParser:
    """Create the standard empty parser state once."""
    return argparse.ArgumentParser(add_help=False)


def _clone_argument_group(
    template: Any,
    parser: argparse.ArgumentParser,
) -> Any:
    """Clone an empty argparse group and bind it to a fresh parser."""
    group = object.__new__(type(template))
    group.__dict__ = template.__dict__.copy()
    group._registries = parser._registries
    group._actions = parser._actions
    group._option_string_actions = parser._option_string_actions
    group._action_groups = []
    group._mutually_exclusive_groups = parser._mutually_exclusive_groups
    group._defaults = parser._defaults
    group._has_negative_number_optionals = parser._has_negative_number_optionals
    group._group_actions = []
    return group


def _new_argument_parser(
    description: str,
    prog: str | None = None,
    usage: str | None = None,
    epilog: str | None = None,
) -> argparse.ArgumentParser:
    """Clone empty argparse state without repeating locale initialization."""
    template = _argument_parser_template()
    parser = object.__new__(argparse.ArgumentParser)
    parser.__dict__ = template.__dict__.copy()
    parser._registries = {
        registry_name: registry.copy()
        for registry_name, registry in template._registries.items()
    }
    parser._actions = []
    parser._option_string_actions = {}
    parser._action_groups = []
    parser._mutually_exclusive_groups = []
    parser._defaults = {}
    parser._has_negative_number_optionals = []
    parser.description = description
    parser.prog = prog if prog is not None else os.path.basename(sys.argv[0])
    parser.usage = usage
    parser.epilog = epilog
    parser._positionals = _clone_argument_group(template._positionals, parser)
    parser._optionals = _clone_argument_group(template._optionals, parser)
    parser._action_groups.extend((parser._positionals, parser._optionals))
    parser._subparsers = None
    return parser


@cache
def _help_action_template() -> argparse.Action:
    """Create the standard argparse help action once."""
    template_parser = argparse.ArgumentParser()
    return template_parser._actions[0]


def _add_help_action(parser: argparse.ArgumentParser) -> None:
    """Attach an independent standard help action to a fresh parser."""
    action = _copy_action(_help_action_template())
    setattr(action, "container", parser._optionals)
    parser._actions.append(action)
    parser._optionals._group_actions.append(action)
    for option in action.option_strings:
        parser._option_string_actions[option] = action
    parser.add_help = True


def _populate_parser(
    parser: argparse.ArgumentParser,
    arg_class: Type["KliamkaArgClass"],
) -> None:
    """Populate an ArgumentParser with arguments from a KliamkaArgClass."""
    try:
        actions, exclusive_groups = _build_parser_plan(arg_class)

        for action in actions:
            parser._add_action(_copy_action(action))

        for _group_name, members in exclusive_groups:
            group = parser.add_mutually_exclusive_group()
            for action in members:
                group._add_action(_copy_action(action))
    except ValueError as exc:
        from ._core import KliamkaError

        raise KliamkaError(str(exc)) from exc
