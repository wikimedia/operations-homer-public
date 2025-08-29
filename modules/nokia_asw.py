"Entry class for access switches."

import importlib


class AccessSwitches:

    def __init__(self, data):
        self._data = data

    _classes: list[str] = [
        "nokia.routing_policy.SrlRoutingPolicy",
        "nokia.interface.SrlInterface",
        "nokia.system.SrlSystem",
        "nokia.network_instance.SrlNetworkInstance",
        "nokia.ospf.SrlOspf",
    ]

    def render(self) -> list:
        generated_config: list = []
        for class_path in self._classes:
            module_name, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            generated_config.extend(
                getattr(module, class_name)(self._data).get_commands()
            )

        return generated_config


python_renderer = AccessSwitches
