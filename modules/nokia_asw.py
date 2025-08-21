"Entry class for access switches."

from nokia.interface import SrlInterface
from nokia.system import SrlSystem


class AccessSwitches:

    def __init__(self, data):
        self._data = data

    def render(self) -> list:
        generated_config: list = []
        generated_config.extend(SrlInterface(self._data).get_commands())
        generated_config.extend(SrlSystem(self._data).get_commands())
        return generated_config


python_renderer = AccessSwitches
