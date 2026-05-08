"""Nokia SR-Linux module for /network-instance/protocols/ospf related configuration."""

from typing import Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlBfd(BaseNokiaRpc):
    _methods = ["srl_bfd"]

    def srl_bfd(self) -> Iterator[NokiaRpc]:
        # BFD needs to be enabled for all sub-interfaces it runs on.  In our setup that is
        # fairly simple it means just system0.0 (IBGP multihop peerings between switches),
        # and irb0 sub-interfaces (peering to BIRD servers in the Anycast group).
        # It seems fairly safe to just enable it for all these, even if at POPs we have
        # no IBGP between loopbacks, or on some Leaf's there will be no hosts that need it
        # enabled on an irb0.

        bfd_config = {"subinterface": [{"id": "system0.0", "admin-state": "enable"}]}
        for int_name in self._data["netbox"]["device_plugin"]["device_interfaces"].keys():
            if int_name.startswith("irb0."):
                bfd_config["subinterface"].append({"id": int_name, "admin-state": "enable"})

        yield NokiaRpc(path="/bfd", config=bfd_config)
