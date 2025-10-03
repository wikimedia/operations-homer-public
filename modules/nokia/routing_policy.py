"""Nokia SR-Linux module for /routing-policy related configuration."""

from typing import Iterator

from . import BaseNokiaRpc, NokiaRpc, get_static_config


class SrlRoutingPolicy(BaseNokiaRpc):

    _methods = ["srl_routing_policy"]

    def srl_routing_policy(self) -> Iterator[NokiaRpc]:
        yield NokiaRpc(
            path="/routing-policy",
            config=get_static_config("nokia", "routing_policy"),
        )
