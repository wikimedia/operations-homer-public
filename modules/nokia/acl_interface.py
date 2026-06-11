"""Nokia SR-Linux module for /acl/interface configuration."""

from typing import Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlAclInterface(BaseNokiaRpc):
    _methods = ["srl_acl_interface"]

    def srl_acl_interface(self) -> Iterator[NokiaRpc]:
        """Generate config to attach ACLs to interfaces"""
        yield NokiaRpc(path="/acl/interface", action="delete")

        for int_name, int_data in self._data["netbox"]["device_plugin"]["device_interfaces"].items():
            if not int_name.startswith("irb") or "description" not in int_data:
                continue
            acl_interface = {}
            if "analytics" in int_data["description"]:
                acl_interface = self._get_acl_interface(int_name, "analytics-in")
            elif "sandbox" in int_data["description"]:
                acl_interface = self._get_acl_interface(int_name, "sandbox")
            if acl_interface:
                yield NokiaRpc(path=f"/acl/interface[interface-id={int_name}]", config=acl_interface)

    def _get_acl_interface(self, int_name, acl_name):
        """Returns dict structure of config to attach acl to interface"""
        return {
            "interface-id": int_name,
            "input": {"acl-filter": [{"name": acl_name, "type": "ipv4"}, {"name": acl_name, "type": "ipv6"}]},
        }
