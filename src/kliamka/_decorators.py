import argparse
from functools import wraps
from typing import Any, Callable, Optional, Sequence, Type, TypeVar

from ._core import KliamkaArg, KliamkaArgClass, KliamkaError, ParserMeta
from ._parser import _populate_parser

F = TypeVar("F", bound=Callable[..., Any])

_SUBCOMMAND_DEST = "_command"


def _iter_arg_dests(
    arg_class: Type[KliamkaArgClass],
) -> "list[tuple[str, str, bool]]":
    """List destinations, display names, and CLI-backed status for model fields."""
    dests = []
    for field_name, field_info in arg_class.model_fields.items():
        arg = field_info.default
        if isinstance(arg, KliamkaArg):
            dests.append((arg.name or field_name, arg.flag, True))
        else:
            dests.append((field_name, field_name, False))
    return dests


def _uses_reserved_subcommand_dest(dest: str, flag: str) -> bool:
    """Return whether a field destination or option spelling is reserved."""
    normalized_flag = flag.lstrip("-").replace("-", "_")
    return dest == _SUBCOMMAND_DEST or normalized_flag == _SUBCOMMAND_DEST


def _apply_version_argument(
    parser: argparse.ArgumentParser,
    meta: ParserMeta,
) -> None:
    """Add a version flag configured by ``ParserMeta`` when present."""
    if meta.version is not None:
        parser.add_argument("--version", action="version", version=meta.version)


def _validate_subcommand_dests(
    main_class: Type[KliamkaArgClass],
    subcommands: dict[str, Type[KliamkaArgClass]],
) -> None:
    """Reject argument collisions that argparse would silently misparse.

    Subparsers copy their parsed values onto the main namespace, so an
    argument defined in both the main class and a subcommand would
    clobber the main value without any warning from argparse.

    Raises:
        KliamkaError: If a subcommand argument maps to the same namespace
            attribute as a main argument, or any argument uses the
            reserved ``_command`` name.
    """
    main_dests: dict[str, tuple[str, bool]] = {}
    for dest, flag, is_cli_backed in _iter_arg_dests(main_class):
        if _uses_reserved_subcommand_dest(dest, flag):
            raise KliamkaError(
                f"argument '{flag}' uses the reserved name '{_SUBCOMMAND_DEST}'"
            )
        main_dests[dest] = (flag, is_cli_backed)

    for cmd_name, cmd_class in subcommands.items():
        for dest, flag, is_cli_backed in _iter_arg_dests(cmd_class):
            if _uses_reserved_subcommand_dest(dest, flag):
                raise KliamkaError(
                    f"subcommand '{cmd_name}' argument '{flag}' uses the "
                    f"reserved name '{_SUBCOMMAND_DEST}'"
                )
            if dest not in main_dests:
                continue

            main_flag, main_is_cli_backed = main_dests[dest]
            if is_cli_backed or main_is_cli_backed:
                raise KliamkaError(
                    f"subcommand '{cmd_name}' argument '{flag}' conflicts with "
                    f"main argument '{main_flag}': both parse into '{dest}'"
                )


def kliamka_cli(
    arg_class: Type[KliamkaArgClass],
    argv: Optional[Sequence[str]] = None,
) -> Callable[[F], F]:
    """Decorator that injects CLI arguments as the first parameter."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            parser = arg_class.create_parser()
            parsed_args = parser.parse_args(argv)
            try:
                instance = arg_class.from_args(parsed_args)
            except KliamkaError as exc:
                parser.error(str(exc))
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

    Raises:
        KliamkaError: If a subcommand argument collides with a main-class
            argument (see :func:`_validate_subcommand_dests`).
    """
    _validate_subcommand_dests(main_class, subcommands)

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            meta = main_class._get_parser_meta()
            parser_kwargs: dict[str, Any] = {
                "description": main_class.__doc__ or "",
            }
            if meta.prog is not None:
                parser_kwargs["prog"] = meta.prog
            if meta.usage is not None:
                parser_kwargs["usage"] = meta.usage
            if meta.epilog is not None:
                parser_kwargs["epilog"] = meta.epilog

            parser = argparse.ArgumentParser(**parser_kwargs)
            _apply_version_argument(parser, meta)

            _populate_parser(parser, main_class)

            subparsers = parser.add_subparsers(dest=_SUBCOMMAND_DEST, required=True)
            command_parsers: dict[str, argparse.ArgumentParser] = {}
            for cmd_name, cmd_class in subcommands.items():
                cmd_meta = cmd_class._get_parser_meta()
                sub_parser_kwargs: dict[str, Any] = {
                    "help": cmd_class.__doc__ or "",
                    "description": cmd_class.__doc__ or "",
                }
                if cmd_meta.prog is not None:
                    sub_parser_kwargs["prog"] = cmd_meta.prog
                if cmd_meta.usage is not None:
                    sub_parser_kwargs["usage"] = cmd_meta.usage
                if cmd_meta.epilog is not None:
                    sub_parser_kwargs["epilog"] = cmd_meta.epilog

                sub_parser = subparsers.add_parser(cmd_name, **sub_parser_kwargs)
                command_parsers[cmd_name] = sub_parser
                _apply_version_argument(sub_parser, cmd_meta)
                _populate_parser(sub_parser, cmd_class)

            parsed_args = parser.parse_args(argv)
            command = getattr(parsed_args, _SUBCOMMAND_DEST)

            try:
                main_instance = main_class.from_args(parsed_args)
            except KliamkaError as exc:
                parser.error(str(exc))

            cmd_class = subcommands[command]
            try:
                cmd_instance = cmd_class.from_args(parsed_args)
            except KliamkaError as exc:
                command_parsers[command].error(str(exc))

            return func(main_instance, command, cmd_instance, *args, **kwargs)

        wrapper._kliamka_func = func  # type: ignore[attr-defined]
        wrapper._kliamka_main_class = main_class  # type: ignore[attr-defined]
        wrapper._kliamka_subcommands = subcommands  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
