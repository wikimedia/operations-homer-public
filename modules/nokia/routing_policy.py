"""Nokia SR-Linux module for /routing-policy related configuration."""

from typing import Iterator

from . import BaseNokiaRpc, NokiaRpc, get_static_config


class SrlRoutingPolicy(BaseNokiaRpc):

    _methods = ["srl_routing_policy"]

    def srl_routing_policy(self) -> Iterator[NokiaRpc]:
        srl_major_ver = int(self._data["srlinux_version"].split(".")[0])
        policy_file = "routing_policy_v24" if srl_major_ver < 25 else "routing_policy"
        yield NokiaRpc(
            path="/routing-policy",
            config=get_static_config("nokia", policy_file),
        )
