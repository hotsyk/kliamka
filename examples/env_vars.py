"""Example demonstrating environment variable fallback in kliamka."""

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli


class Environment(Enum):
    """Deployment environment."""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class AppConfig(KliamkaArgClass):
    """Application configuration with environment variable support.

    Try running with environment variables:
        export APP_API_KEY="my-secret-key"
        export APP_DEBUG="true"
        export APP_PORT="3000"
        export APP_ENV="prod"
        python env_vars.py
    """

    api_key: Optional[str] = KliamkaArg(
        "--api-key",
        "API key for authentication",
        env="APP_API_KEY",
    )
    debug: Optional[bool] = KliamkaArg(
        "--debug",
        "Enable debug mode",
        env="APP_DEBUG",
    )
    port: Optional[int] = KliamkaArg(
        "--port",
        "Server port",
        default=8080,
        env="APP_PORT",
    )
    environment: Optional[Environment] = KliamkaArg(
        "--env",
        "Deployment environment",
        default=Environment.DEV,
        env="APP_ENV",
    )
    verbose: Optional[bool] = KliamkaArg("--verbose", "Enable verbose output")


@kliamka_cli(AppConfig)
def main(args: AppConfig) -> None:
    """Demonstrate environment variable fallback usage.

    Priority order: CLI argument > Environment variable > Default value
    """
    print("Kliamka Environment Variable Example")
    print(f"API Key: {'*' * len(args.api_key) if args.api_key else 'Not set'}")
    print(f"Debug Mode: {args.debug}")
    print(f"Port: {args.port}")
    print(f"Environment: {args.environment.value if args.environment else 'Not set'}")

    if args.verbose:
        print("\nVerbose mode enabled:")
        print("  Environment variables checked:")
        print("    APP_API_KEY -> --api-key")
        print("    APP_DEBUG -> --debug")
        print("    APP_PORT -> --port")
        print("    APP_ENV -> --env")
        print("\n  Priority: CLI > ENV > Default")


if __name__ == "__main__":
    main()
