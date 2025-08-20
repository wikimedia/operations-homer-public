from dataclasses import dataclass
from typing import Any


# The kw_only bit requires Python 3.10+
@dataclass(frozen=True, kw_only=True)  # type: ignore[call-overload]
class NokiaRpc:

    path: str
    config: Any
    action: str = "replace"

    def get_command(self):
        return {"action": self.action, "path": self.path, "value": self.config}


class BaseNokiaRpc:

    _methods: list[str] = []

    def __init__(self, data: dict):
        self._data = data

    def get_commands(self) -> list[dict]:
        commands = []
        for method_name in self._methods:
            commands.extend(
                [command.get_command() for command in getattr(self, method_name)()]
            )

        return commands
