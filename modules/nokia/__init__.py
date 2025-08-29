import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from homer.exceptions import HomerError

logger = logging.getLogger(__name__)
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


def get_static_config(*args: str):
    # double parent seems needed
    path = str(
        Path(__file__).parent.parent.joinpath("static", *args).with_suffix(".yaml")
    )
    logger.debug("Importing YAML file: %s", path)
    return path
    # the str() is needed until we convert the whole homer to use pathlib
