"""Nokia SR-Linux module for /network-instance/protocols/ospf related configuration."""

from ipaddress import ip_interface
from typing import Any, Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlOspf(BaseNokiaRpc):
    # We only have OSPF in the default instance
    _methods = ["srl_ospf"]

    def srl_ospf(self) -> Iterator[NokiaRpc]:
        # TODO as we need the router ID for BGP too maybe move those few lines
        # to nokia_asw.py to "enrich" the data dict.
        device_ints = self._data["netbox"]["device_plugin"]["device_interfaces"]
        # Use IPv4 address of system0 int as Router ID
        for address in device_ints["system0"]["ip_addresses"]:
            if address["family"]["value"] == 4:
                router_id = str(ip_interface(address["address"]).ip)

        ibgp_config = self._data["netbox"]["device_plugin"]["ibgp_config"]
        ospf: dict[str, list[dict]] = {"instance": []}

        ospf_interfaces = []
        # Add the required interfaces
        for int_name in ibgp_config["ospf_ints"]:
            int_conf = {"interface-name": f"{int_name}.0"}
            if int_name != "system0":
                int_conf["interface-type"] = "point-to-point"
            ospf_interfaces.append(int_conf)

        for ospf_version in (
            ("ospf-v2", "ospf-v3") if ibgp_config["ospf3"] else ("ospf-v2",)
        ):
            instance_conf: dict[str, Any] = {
                "name": ospf_version.replace("-", ""),
                "admin-state": "enable",
                "version": ospf_version,
                "router-id": router_id,
                "max-ecmp-paths": 64,
                "reference-bandwidth": "800000000",
                "area": [{"area-id": "0.0.0.0", "interface": ospf_interfaces}],
            }
            if ospf_version == "ospf-v3":
                instance_conf["address-family"] = "ipv6-unicast"

            ospf["instance"].append(instance_conf)
        # This needs to happen after the initial network-instances are defined in SrlNetworkInstance
        yield NokiaRpc(
            path="/network-instance[name=default]/protocols/ospf", config=ospf
        )
