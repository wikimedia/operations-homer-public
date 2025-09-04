"""Nokia SR-Linux module for /network-instance related configuration."""

from ipaddress import ip_interface
from typing import Any, Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlNetworkInstance(BaseNokiaRpc):

    _methods = ["srl_network_instance", "srl_vxlan_interface"]

    def __init__(self, data: dict) -> None:
        super().__init__(data)

    def srl_network_instance(self) -> Iterator[NokiaRpc]:
        """Returns commands to replace all /network-instance configuration in a Nokia format."""
        device_ints = self._data["netbox"]["device_plugin"]["device_interfaces"]

        # First we send the command to delete all the network instances
        yield NokiaRpc(path="/network-instance", action="delete")

        # Generate and add the VRF config to our commands
        for vrf_name, vrf_data in self._data["vrfs"].items():
            vrf_conf = base_vrf_conf(vrf_name, vrf_data, self._data)
            if vrf_name == "mgmt":
                mgmt_ip = device_ints["mgmt0"]["ip_addresses"][0]["address"]
                vrf_conf.update(mgmt_vrf_conf(mgmt_ip))
            yield NokiaRpc(path=f"/network-instance[name={vrf_name}]", config=vrf_conf)

        # Generate and add the commands to config mac-vrf's i.e. vlans
        for vlan_name, vlan_data in self._data["vlans"].items():
            vlan_conf = base_vlan_conf(vlan_name, vlan_data, self._data["evpn"])
            yield NokiaRpc(
                path=f"/network-instance[name=vlan-{vlan_data['vid']}]",
                config=vlan_conf,
            )

    def srl_vxlan_interface(self) -> Iterator[NokiaRpc]:
        """Returns command to configure the vxlan0 tunnel-interface."""
        # If not EVPN we stop there
        if not self._data["evpn"]:
            return
        vxlan0_conf: list[dict[str, Any]] = [{"name": "vxlan0", "vxlan-interface": []}]

        for _, vlan_data in self._data["vlans"].items():
            vxlan0_conf[0]["vxlan-interface"].append(
                {
                    "index": vlan_data["vid"],
                    "type": "bridged",
                    "ingress": {"vni": f"200{vlan_data['vid']}"},
                }
            )

        for vrf_name, vrf_data in self._data["vrfs"].items():
            if vrf_name.startswith(("mgmt", "default")):
                continue
            vxlan0_conf[0]["vxlan-interface"].append(
                {
                    "index": vrf_data["rd"],
                    "type": "routed",
                    "ingress": {"vni": f"300{vrf_data['rd']}"},
                }
            )
        # Otherwise we also include the vxlan0 tunnel-interface config
        yield NokiaRpc(path="/tunnel-interface[name=vxlan0]", config=vxlan0_conf)


def add_vlan_int(int_name: str, vlan: dict, vlans: dict):
    """Appends int_name to the vlans dict, plus the vlan itself if it's not already there"""
    vlan_name = vlan["name"]
    subint_name = (
        int_name if len(int_name.split(".")) == 2 else f"{int_name}.{vlan['vid']}"
    )
    if vlan_name not in vlans:
        vlans[vlan_name] = {"vid": vlan["vid"], "interfaces": [subint_name]}
    else:
        vlans[vlan_name]["interfaces"].append(subint_name)


def base_vlan_conf(vlan_name: str, vlan_data: dict, evpn: bool) -> dict:
    """Returns base network-instance configuration for a L2 vlan"""
    vlan_conf = {
        "name": f"vlan-{vlan_data['vid']}",
        "description": vlan_name,
        "type": "mac-vrf",
        "admin-state": "enable",
        "interface": [{"name": int_name} for int_name in vlan_data["interfaces"]],
        "bridge-table": {"mac-learning": {"aging": {"age-time": 1200}}},
    }
    if evpn:
        vlan_conf.update(
            instance_evpn_conf(instance_id=vlan_data["vid"], l3_instance=False)
        )
    return vlan_conf


def base_vrf_conf(vrf_name: str, vrf_data: dict, data: dict) -> dict:
    """Returns base configuration for L3 VRF config in SR Linux format"""
    base_vrf: dict[str, Any] = {
        "name": vrf_name,
        "type": "default" if vrf_name == "default" else "ip-vrf",
        "admin-state": "enable",
        "protocols": {},
        "interface": [{"name": int_name} for int_name in vrf_data["interfaces"]],
    }
    if data["evpn"] and "rd" in vrf_data and vrf_data["rd"]:
        base_vrf.update(
            instance_evpn_conf(instance_id=vrf_data["rd"], l3_instance=True)
        )
    return base_vrf


def mgmt_vrf_conf(mgmt_ip) -> dict:
    """Returns the bespoke config we need in the mgmt VRF"""
    ip_addr = ip_interface(mgmt_ip)
    return {
        "description": "Management network instance",
        "protocols": {
            "linux": {
                "import-routes": True,
                "export-routes": True,
                "export-neighbors": True,
            }
        },
        "static-routes": {
            "route": [{"prefix": "0.0.0.0/0", "next-hop-group": "mgmt_gw"}]
        },
        "next-hop-groups": {
            "group": [
                {
                    "name": "mgmt_gw",
                    "nexthop": [{"index": 0, "ip-address": str(ip_addr.network[1])}],
                }
            ]
        },
    }


def instance_evpn_conf(instance_id: int, l3_instance: bool) -> dict:
    """Returns additional instance config to bind it to EVPN/VXLAN VNI"""
    return {
        "vxlan-interface": [{"name": f"vxlan0.{instance_id}"}],
        "protocols": {
            "bgp-evpn": {
                "bgp-instance": [
                    {
                        "id": 1,
                        "admin-state": "enable",
                        "vxlan-interface": f"vxlan0.{instance_id}",
                        "evi": instance_id,
                        "ecmp": 32 if l3_instance else 8,
                    }
                ]
            },
            "bgp-vpn": {"bgp-instance": [{"id": 1}]},
        },
    }


def get_required_instances(data: dict) -> tuple[dict, dict]:
    """Returns the list of VRFs and Vlans needed on the device based on interface membership"""
    # TODO: this is the kind of thing that maybe should be split and the "common" parts done
    # in homer or the plugin so we don't build the list twice for Juniper/Nokia

    # Init dict with the two default VRFs
    vrfs: dict[str, dict[str, Any]] = {
        "mgmt": {"rd": None, "interfaces": []},
        "default": {"rd": None, "interfaces": []},
    }
    vlans: dict[str, dict] = {}
    for int_name, int_data in data["netbox"]["device_plugin"][
        "device_interfaces"
    ].items():
        if not int_data["enabled"]:
            continue

        # MGMT Interface - add to management VRF
        if int_data["mgmt_only"]:
            vrfs["mgmt"]["interfaces"].append(f"{int_name}.0")
            continue

        # L3 Interface - extract VRF info and add to vrf dict
        if int_data["ip_addresses"]:
            subint_name = int_name if len(int_name.split(".")) == 2 else f"{int_name}.0"
            if int_data["vrf"]:
                # VRF set in Netbox - add to specific one
                vrf_name = int_data["vrf"]["name"]
                if vrf_name not in vrfs:
                    vrfs[vrf_name] = {"rd": int_data["vrf"]["rd"], "interfaces": []}
                vrfs[vrf_name]["interfaces"].append(subint_name)
            else:
                # No VRF set in Netbox - add to default
                vrfs["default"]["interfaces"].append(subint_name)

        # L2 Interface - extract Vlan info and add to vlans dict
        if int_data["mode"]:
            for vlan in int_data["tagged_vlans"]:
                add_vlan_int(int_name, vlan, vlans)
            if int_data["untagged_vlan"]:
                add_vlan_int(int_name, int_data["untagged_vlan"], vlans)

    return vlans, vrfs
