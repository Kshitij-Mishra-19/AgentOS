from typing import Any, Callable


def echo(message: str) -> str:
    return message


def slow_test() -> str:
    import time

    time.sleep(5)
    return "Finished"


TOOL_HANDLERS: dict[str, Callable[..., Any]] = {
    "echo": echo,
    "slow_test": slow_test,
}