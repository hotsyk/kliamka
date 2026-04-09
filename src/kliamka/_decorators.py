import argparse
from functools import wraps
from typing import Any, Callable, Optional, Sequence, Type, TypeVar

from ._core import KliamkaArgClass, KliamkaError
from ._parser import _populate_parser

F = TypeVar("F", bound=Callable[..., Any])


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
    """Decorator for CLI applications with subcommands."""

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

            try:
                main_instance = main_class.from_args(parsed_args)
                cmd_class = subcommands[command]
                cmd_instance = cmd_class.from_args(parsed_args)
            except KliamkaError as exc:
                parser.error(str(exc))

            return func(main_instance, command, cmd_instance, *args, **kwargs)

        wrapper._kliamka_func = func  # type: ignore[attr-defined]
        wrapper._kliamka_main_class = main_class  # type: ignore[attr-defined]
        wrapper._kliamka_subcommands = subcommands  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
