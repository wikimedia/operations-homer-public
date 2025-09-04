"Entry class for access switches."

import importlib
from ipaddress import ip_interface

from nokia.network_instance import get_required_instances


class AccessSwitches:

    def __init__(self, data):
        self._data = self._get_asw_data(data)

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

    def _get_asw_data(self, data) -> dict:
        """Data-mangling for some common elements to augment data dict passed from Homer"""
        device_ints = data["netbox"]["device_plugin"]["device_interfaces"]
        # IPv4 address of system0 int is used as Router ID
        for address in device_ints["system0"]["ip_addresses"]:
            if address["family"]["value"] == 4:
                data["router_id"] = str(ip_interface(address["address"]).ip)
                break

        data["evpn"] = data["netbox"]["device_plugin"]["ibgp_config"]["evpn"]
        # Compile the vlans and vrfs we need to configure, plus member interfaces
        data["vlans"], data["vrfs"] = get_required_instances(data)

        return data


python_renderer = AccessSwitches
