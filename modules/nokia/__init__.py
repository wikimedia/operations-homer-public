import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
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
    """Loads static config from a YAML file in the 'static' dir"""
    # double parent seems needed
    path = Path(__file__).parent.parent.joinpath("static", *args).with_suffix(".yaml")

    logger.debug("Importing YAML file: %s", path)

    if not path.exists():
        raise HomerError(f"Static config file at {path} not found.")

    try:
        with path.open("r", encoding="utf-8") as fh:
            config = yaml.load(fh, Loader=yaml.FullLoader)  # nosec B506

    except Exception as e:
        raise HomerError(f"Could not load config file {path}: {e}") from e

    return config or {}
