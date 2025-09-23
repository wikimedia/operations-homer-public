"""Nokia SR-Linux module for /interface related configuration."""

from collections import defaultdict
from ipaddress import ip_interface
from typing import Any, Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlInterface(BaseNokiaRpc):

    _methods = ["srl_interface"]

    def srl_interface(self) -> Iterator[NokiaRpc]:
        """Returns commands to individually replace all /interface configuration in a Nokia format."""
        yield NokiaRpc(path="/interface", action="delete")
        interfaces: list[dict[str, Any]] = []

        sub_ints: dict[str, Any] = defaultdict(dict)

        for int_name, int_data in self._data["netbox"]["device_plugin"][
            "device_interfaces"
        ].items():
            # If it's a sub-interface just record for later and continue
            if int_data["type"] == "virtual" and int_data["parent"]:
                parent = int_data["parent"]["name"]
                sub_ints[parent][int_name] = int_data
                continue

            srl_int = get_srl_base_int(int_name, int_data)
            # Access interface
            if int_data["mode"] == "access":
                srl_int.update(get_srl_access_int(int_data))
            # Trunk interface
            if int_data["mode"] == "tagged":
                srl_int.update(get_srl_trunk_int(int_data))
            # Routed interface
            if int_data["ip_addresses"]:
                srl_int["subinterface"] = [
                    get_srl_routed_subint(0, int_data, self._data)
                ]

            interfaces.append(
                {
                    "path": f"/interface[name={int_name}]",
                    "value": srl_int,
                }
            )

        # Now loop over the interface config we built and add subints to parents where needed
        for interface in interfaces:
            if interface["value"]["name"] in sub_ints:
                parent_name = interface["value"]["name"]
                if parent_name.startswith("ethernet-1"):
                    interface["value"]["vlan-tagging"] = True
                interface["value"]["subinterface"] = get_srl_l3_subints(
                    sub_ints[parent_name], self._data
                )
        for interface in interfaces:
            yield NokiaRpc(path=interface["path"], config=interface["value"])


def get_srl_base_int(int_name: str, int_data: dict) -> dict:
    """Gets common base interface dict"""
    base_int: dict[str, Any] = {
        "name": int_name,
        "admin-state": "enable" if int_data["enabled"] else "disable",
    }
    if int_data["description"]:
        base_int["description"] = int_data["description"]

    # Set FEC to match Juniper default if other side is QFX
    if (
        int_data["enabled"]
        and int_data["connected_endpoints"]
        and int_data["type"].startswith("100gbase")
        and int_data["connected_endpoints"][0]["__typename"] == "InterfaceType"
        and int_data["connected_endpoints"][0]["device"]["role"]["slug"] == "asw"
        and int_data["connected_endpoints"][0]["device"]["device_type"]["manufacturer"][
            "slug"
        ]
        == "juniper"
    ):
        # TODO: How to model this and work for every variant, below works for SR4 matching QFX default
        base_int["transceiver"] = {"forward-error-correction": "rs-528"}

    return base_int


def get_srl_access_int(int_data: dict) -> dict:
    """Returns dict elements for untagged access interface"""
    return {
        "sflow": {"admin-state": "enable"},
        "vlan-tagging": False,
        "subinterface": [
            {
                "index": int_data["untagged_vlan"]["vid"],
                "type": "bridged",
                "admin-state": "enable",
            }
        ],
    }


def get_srl_trunk_int(int_data: dict) -> dict:
    """Returns dict elements for tagged trunk interface"""
    trunk_int: dict[str, Any] = {
        "sflow": {"admin-state": "enable"},
        "vlan-tagging": True,
        "subinterface": [],
    }
    for tagged_vlan in int_data["tagged_vlans"]:
        trunk_int["subinterface"].append(
            {
                "index": tagged_vlan["vid"],
                "type": "bridged",
                "admin-state": "enable",
                "vlan": {"encap": {"single-tagged": {"vlan-id": tagged_vlan["vid"]}}},
            }
        )
    if int_data["untagged_vlan"]:
        trunk_int["subinterface"].append(
            {
                "index": int_data["untagged_vlan"]["vid"],
                "type": "bridged",
                "admin-state": "enable",
                "vlan": {"encap": {"untagged": {}}},
            }
        )
    return trunk_int


def get_srl_l3_subints(interface_subs: dict, data: dict) -> list:
    """Generates list with all routed sub-int configs for a parent"""
    subinterfaces = []
    for subint_name, subint_data in interface_subs.items():
        subint_index = int(subint_name.split(".")[-1])
        subint_conf = get_srl_routed_subint(subint_index, subint_data, data)
        if subint_data["parent"]["name"].startswith("ethernet-1"):
            subint_conf["vlan"] = {
                "encap": {"single-tagged": {"vlan-id": subint_index}}
            }
        subinterfaces.append(subint_conf)
    return subinterfaces


def get_srl_routed_subint(index, int_data: dict, data: dict) -> dict:
    """Gets config block for a single routed sub-interface"""
    subint = {"index": index, "admin-state": "enable"}

    # Check based on roles set on the interface IPs if this is anycast gw
    anycast_gw = ""
    if any(int_addr["role"] == "anycast" for int_addr in int_data["ip_addresses"]):
        subint["anycast-gw"] = {}
        if any(int_addr["role"] != "anycast" for int_addr in int_data["ip_addresses"]):
            anycast_gw = "dual"
        else:
            anycast_gw = "single"

    # Now add each address defined for the int
    for int_addr in int_data["ip_addresses"]:
        address_fam = f"ipv{int_addr['family']['value']}"
        # Add the address-fam block to the subinterface if needed:
        if address_fam not in subint:
            subint[address_fam] = {"admin-state": "enable", "address": []}
            # Additional config is needed on IRB interfaces
            if int_data["name"].startswith("irb"):
                if data["evpn"]:
                    subint[address_fam].update(get_irb_evpn_conf(address_fam))
                if int_data["description"].startswith(("private", "analytics")):
                    if address_fam == "ipv4":
                        subint[address_fam]["dhcp-relay"] = {
                            "gi-address": data["loopbacks"]["external"]["4"],
                            "use-gi-addr-as-src-ip-addr": True,
                            "network-instance": data["loopbacks"]["external"]["vrf"],
                            "server": [data["dhcp_server"]["ip"].compressed],
                        }
                    if address_fam == "ipv6":
                        prefix = ip_interface(int_addr["address"]).network
                        subint[address_fam]["router-advertisement"] = {
                            "router-role": {
                                "admin-state": "enable",
                                "min-advertisement-interval": 30,
                                "router-lifetime": 600,
                                "prefix": [{"ipv6-prefix": prefix.with_prefixlen}],
                            }
                        }

        # Now add the current IP to the address fam block for this subint
        subint[address_fam]["address"].append({"ip-prefix": int_addr["address"]})
        # On anycast GW set the flags we need for the address
        if int_addr["role"] == "anycast":
            subint[address_fam]["address"][-1]["anycast-gw"] = True
        if (int_addr["role"] != "anycast" and anycast_gw) or anycast_gw == "single":
            subint[address_fam]["address"][-1]["primary"] = [None]

    return subint


def get_irb_evpn_conf(address_fam: str) -> dict:
    """Return dict with ARP -> EVPN route export and timeout settings for irb address fam block"""
    irb_evpn_conf = {}
    arp_route_conf: dict[str, Any] = {
        "host-route": {"populate": [{"route-type": "dynamic"}]},
        "evpn": {"advertise": [{"route-type": "dynamic"}]},
    }
    if address_fam == "ipv4":
        irb_evpn_conf["arp"] = arp_route_conf
        irb_evpn_conf["arp"]["learn-unsolicited"] = True
        irb_evpn_conf["arp"]["timeout"] = 600
    else:
        irb_evpn_conf["neighbor-discovery"] = arp_route_conf
        irb_evpn_conf["neighbor-discovery"]["learn-unsolicited"] = "global"
        irb_evpn_conf["neighbor-discovery"]["stale-time"] = 600
    return irb_evpn_conf
