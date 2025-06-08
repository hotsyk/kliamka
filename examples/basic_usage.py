"""Basic usage example for kliamka library."""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kliamka import KliamkaArg, KliamkaArgClass, kliamka_cli


class KliamkaArgClassExample(KliamkaArgClass):
    show_doc: Optional[bool] = KliamkaArg("--show-doc", default=False, help_text="Show documentation")
    counter: int = KliamkaArg("--counter", help_text="Counter value", default=0)


@kliamka_cli(KliamkaArgClassExample)
def main(kliamka_class) -> None:
    """Demonstrate basic kliamka functionality."""
    print("Kliamka CLI Example")
    if kliamka_class.show_doc:
        print("Show Documentation requested. Use --help to see available options.")
    else:
        print("No show Documentation requested. Running main function.")

    print(f"Counter value: {kliamka_class.counter}")


if __name__ == "__main__":
    main()
