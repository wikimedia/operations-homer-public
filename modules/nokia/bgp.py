"""Nokia SR-Linux module for /network-instance/protocols/ospf related configuration."""

from typing import Any, Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlBgp(BaseNokiaRpc):
    _methods = ["srl_bgp"]

    def srl_bgp(self) -> Iterator[NokiaRpc]:
        # BGP config is nested in the network-instance config, so we build for each
        for vrf_name, vrf_data in self._data["vrfs"].items():
            instance_bgp_conf = self._get_instance_bgp_conf(vrf_name, vrf_data)
            if not instance_bgp_conf:
                continue
            yield NokiaRpc(
                path=f"/network-instance[name={vrf_name}]/protocols/bgp",
                config=instance_bgp_conf,
            )

    def _get_instance_bgp_conf(self, vrf_name: str, vrf_data: dict) -> dict:
        """Generates the full BGP config for a given network instance"""
        ibgp_data = self._data["netbox"]["device_plugin"]["ibgp_config"]
        bgp_config = self._get_base_bgp_config(ibgp_data)

        # IBGP config is only in the default network instance
        if vrf_name == "default":
            ibgp_groups = (
                ["ibgp_evpn"] if ibgp_data["evpn"] else ["ibgp_ipv4", "ibgp_ipv6"]
            )
            for group in ibgp_groups:
                address_fams = (
                    ["evpn"]
                    if ibgp_data["evpn"]
                    else [f"{group.split('_')[-1]}-unicast"]
                )
                # TODO - get the policy names for the group, add them to _data["required_items"]
                bgp_config["group"].append(
                    self._get_bgp_group(
                        group, ibgp_data["asn"], "ALL", "ALL", address_fams
                    )
                )
                bgp_config["neighbor"].extend(self._get_ibgp_neighbors(ibgp_data))
            if ibgp_data["rr"]:
                bgp_config["route-reflector"] = {"cluster-id": self._data["router_id"]}

        # TODO - Add EBGP neighbors (hosts and manually defined in YAML)

        # If this instance has no neighbors return an empty dict i.e. no bgp config
        if not bgp_config["neighbor"]:
            return {}

        # Work out what AFI-SAFIs we have enabled across all groups, and enable them at the instance level
        afi_safis = set()
        for bgp_group in bgp_config["group"]:
            for afi_safi in bgp_group["afi-safi"]:
                afi_safis.add(afi_safi["afi-safi-name"])

        for afi_safi in afi_safis:
            bgp_config["afi-safi"].append(
                {
                    "afi-safi-name": afi_safi,
                    "admin-state": "enable",
                    "multipath": {"maximum-paths": 64},
                }
            )
        # Lastly disable any afi-safis enabled at the top level if they are not needed for a group
        for bgp_group in bgp_config["group"]:
            group_afi_safis = [
                afi_safi["afi-safi-name"] for afi_safi in bgp_group["afi-safi"]
            ]
            for afi_safi in afi_safis:
                if afi_safi not in group_afi_safis:
                    bgp_group["afi-safi"].append(
                        {"afi-safi-name": afi_safi, "admin-state": "disable"}
                    )

        return bgp_config

    def _get_base_bgp_config(self, ibgp_data: dict) -> dict:
        """Gets the basic dict structure for the BGP part of a net instance config"""
        return {
            "router-id": self._data["router_id"],
            "autonomous-system": ibgp_data["asn"],
            "failure-detection": {"fast-failover": True},
            "afi-safi": [],
            "group": [],
            "neighbor": [],
        }

    def _get_bgp_group(
        self,
        bgp_group_name: str,
        peer_as: int,
        import_pol: str,
        export_pol: str,
        address_fams: list[str],
    ) -> dict[str, Any]:
        """Generates a BGP group configuration block for inside a network instance"""
        group_config: dict[str, Any] = {
            "group-name": bgp_group_name,
            "peer-as": peer_as,
            "export-policy": [export_pol],
            "import-policy": [import_pol],
            "afi-safi": [],
        }
        for address_fam in address_fams:
            group_config["afi-safi"].append(
                {"afi-safi-name": address_fam, "admin-state": "enable"}
            )
        return group_config

    def _get_ibgp_neighbors(self, ibgp_data: dict) -> list:
        """Parse ibgp_data from the wmf_plugin and build up the neighbor configs by running _get_bgp_neighbors()
        with the correct vars"""
        ibgp_neighbors = []
        for peer_name, peer_data in ibgp_data["peers"].items():
            for ip_version, ip_address in peer_data["addresses"].items():
                peer_group = (
                    "ibgp_evpn" if ibgp_data["evpn"] else f"ibgp_ipv{ip_version}"
                )
                ibgp_neighbors.append(
                    self._get_bgp_neighbor(
                        peer_group=peer_group,
                        peer_name=peer_name,
                        peer_ip=ip_address,
                        source_ip=ibgp_data["source_ips"][ip_version],
                        rr_client=peer_data["rr_client"],
                        bfd=True,
                    )
                )

        return ibgp_neighbors

    def _get_bgp_neighbor(
        self,
        peer_group: str,
        peer_name: str,
        peer_ip: str,
        source_ip: str = "",
        rr_client: bool = False,
        bfd: bool = False,
    ) -> dict[str, Any]:
        """Gets the config block for a specific BGP neighbor"""
        neigh_conf: dict[str, Any] = {
            "peer-address": peer_ip,
            "description": peer_name,
            "peer-group": peer_group,
        }
        if source_ip:
            neigh_conf["transport"] = {"local-address": source_ip}
        if rr_client:
            neigh_conf["route-reflector"] = {"client": True}
        if bfd:
            neigh_conf["failure-detection"] = {
                "enable-bfd": True,
                "fast-failover": True,
            }
        return neigh_conf
