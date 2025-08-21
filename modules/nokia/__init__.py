from dataclasses import dataclass
from typing import Any

from homer.exceptions import HomerError

NoConfig = object()


# The kw_only bit requires Python 3.10+
@dataclass(frozen=True, kw_only=True)  # type: ignore[call-overload]
class NokiaRpc:

    path: str
    config: Any = NoConfig
    action: str = "replace"

    def __post_init__(self):
        if self.config is NoConfig:  # option B
            if self.action != "delete":
                raise HomerError(f"Action '{self.action}' but config missing.")
        else:
            if self.action == "delete":
                raise HomerError(
                    f"Action 'delete' but config '{self.config}' provided."
                )

    def get_command(self):
        command = {"action": self.action, "path": self.path}
        if self.action != "delete":
            command["value"] = self.config
        return command


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
