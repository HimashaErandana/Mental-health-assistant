import logging
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def get_logger(name: str = "app") -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )
    return logging.getLogger(name)
