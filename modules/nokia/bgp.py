"""Nokia SR-Linux module for /network-instance/protocols/ospf related configuration."""

from typing import Any, Iterator, Optional, Tuple

from . import BaseNokiaRpc, NokiaRpc, get_static_config


class SrlBgp(BaseNokiaRpc):
    _methods = ["srl_bgp"]

    def srl_bgp(self) -> Iterator[NokiaRpc]:
        self._data["routing_policy_names"] = self._get_policy_names()
        default_ebgp_vrf = "PRODUCTION" if self._data["evpn"] else "default"
        # BGP config is nested in the network-instance config, so we build for each
        for vrf_name, vrf_data in self._data["vrfs"].items():
            vrf_data["default_ebgp"] = True if vrf_name == default_ebgp_vrf else False
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
                        bgp_group_name=group,
                        import_pol="ALL",
                        export_pol="ALL",
                        address_fams=address_fams,
                        peer_as=ibgp_data["asn"],
                    )
                )
                bgp_config["neighbor"].extend(self._get_ibgp_neighbors(ibgp_data))
            if ibgp_data["rr"]:
                bgp_config["route-reflector"] = {"cluster-id": self._data["router_id"]}

        ebgp_groups, ebgp_neighbors = self._get_ebgp_conf(vrf_name, vrf_data)
        bgp_config["group"].extend(ebgp_groups)
        bgp_config["neighbor"].extend(ebgp_neighbors)

        # If this instance has no neighbors return an empty dict i.e. no bgp config
        if not bgp_config["neighbor"]:
            return {}

        # Work out what AFI-SAFIs we have enabled across all groups, and enable them at the instance level
        afi_safis = set()
        for bgp_group in bgp_config["group"]:
            for afi_safi in bgp_group["afi-safi"]:
                afi_safis.add(afi_safi["afi-safi-name"])

        for afi_safi in afi_safis:
            multipath_conf: dict[str, Any]
            if self._data["srlinux_version"].startswith("24"):
                multipath_conf = {"maximum-paths": 64}
            else:
                multipath_conf = {
                    "ebgp": {"maximum-paths": 64},
                    "ibgp": {"maximum-paths": 64},
                }
            bgp_config["afi-safi"].append(
                {
                    "afi-safi-name": afi_safi,
                    "admin-state": "enable",
                    "multipath": multipath_conf,
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
        address_fams: list[str],
        peer_as: Optional[int] = None,
        import_pol: str = "NONE",
        export_pol: str = "NONE",
    ) -> dict[str, Any]:
        """Generates a BGP group configuration block for inside a network instance"""
        group_config: dict[str, Any] = {
            "group-name": bgp_group_name,
            "export-policy": [export_pol],
            "import-policy": [import_pol],
            "afi-safi": [],
        }
        if peer_as:
            group_config["peer-as"] = peer_as
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
        peer_as: Optional[int] = None,
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
        if peer_as:
            neigh_conf["peer-as"] = peer_as
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

    def _get_ebgp_conf(
        self, vrf_name: str, vrf_data: dict[str, Any]
    ) -> tuple[list, list]:
        """Generates the BGP neighbor and group configs for EBGP peers

        Returns two lists:
            groups:    A list of BGP group configurations that gets appended to
                       /network-instance[name={vrf_name}]/protocols/bgp/group/
            neighbors: A list of BGP neighbor configs that gets appended to
                       /network-instance[name={vrf_name}]/protocols/bgp/neighbor/
        """

        device_bgp = self._data.get("device_bgp", {})
        bgp_servers = self._data["netbox"]["device_plugin"]["bgp_servers"]
        site = self._data["metadata"]["site"]

        neighbors = []
        groups = []
        for peer_group, bgp_peers in (device_bgp | bgp_servers).items():
            address_fams = []
            required_groups = set()

            # Get group ASN. Per-site or global, default to 0 for groups where each peer is different
            group_data = self._data["bgp_group_data"].get(peer_group, {})
            asns = group_data.get("asns", {})
            group_peer_as = asns.get(site, asns.get("global", 0))

            # Loop over peers extracting group info as needed and adding to neighbor list
            for peer_name, peer_config in bgp_peers.items():
                # If we are in the wrong VRF for the peer continue
                if (
                    not vrf_data["default_ebgp"]
                    and peer_config.get("vrf", "") != vrf_name
                ):
                    continue
                for address_fam in (4, 6):
                    if address_fam not in peer_config:
                        continue
                    bgp_group_name = f"{peer_group}{address_fam}"
                    required_groups.add(bgp_group_name)
                    peer_as = peer_config.get("peer_as", 0)
                    neighbors.append(
                        self._get_bgp_neighbor(
                            peer_group=bgp_group_name,
                            peer_name=peer_name,
                            peer_as=peer_as,
                            peer_ip=peer_config[address_fam].compressed,
                            bfd=group_data.get("BFD", False),
                        )
                    )

            # Now build the group configs as needed, we may have two groups (v4 and v6) for each
            for bgp_group_name in required_groups:
                address_fams = [bgp_group_name[-1]]
                # Exception for Pybal group where we use IPv4 transport to also exchange IPv6 NLRIs
                if bgp_group_name == "pybal4":
                    address_fams = ["4", "6"]
                afi_safis = [
                    f"ipv{address_fam}-unicast" for address_fam in address_fams
                ]
                import_pol, export_pol = self._get_bgp_group_policy(bgp_group_name)
                groups.append(
                    self._get_bgp_group(
                        bgp_group_name=bgp_group_name,
                        import_pol=import_pol,
                        export_pol=export_pol,
                        address_fams=afi_safis,
                        peer_as=group_peer_as,
                    )
                )

        return groups, neighbors

    def _get_policy_names(self) -> list[str]:
        """Parses the policies defined in YAML and returns a list of their names"""
        routing_policy = get_static_config("nokia", "routing_policy")
        policies = routing_policy["policy"]
        policy_names = [policy["name"] for policy in policies]
        return policy_names

    def _get_bgp_group_policy(self, bgp_group_name: str) -> Tuple[str, str]:
        """Returns the name of a defined policy matching the bgp group name, or NONE"""
        policies = {
            "in": "NONE",
            "out": "NONE",
        }
        # Check if there are policies defined which match {group_name}_out, {group_name}_in etc.
        for policy_direction in policies.keys():
            # Separate policies per group/address-fam, i.e. evpn_external4_out, evpn_external6_out
            if (
                f"{bgp_group_name}_{policy_direction}"
                in self._data["routing_policy_names"]
            ):
                policies[policy_direction] = f"{bgp_group_name}_{policy_direction}"
            # Single policy for both address-fam groups, i.e. evpn_external_in
            elif (
                f"{bgp_group_name[:-1]}_{policy_direction}"
                in self._data["routing_policy_names"]
            ):
                policies[policy_direction] = f"{bgp_group_name[:-1]}_{policy_direction}"

        return policies["in"], policies["out"]
