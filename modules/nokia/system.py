"""Nokia SR-Linux module for /system related configuration."""

from typing import Iterator

from . import BaseNokiaRpc, NokiaRpc


class SrlSystem(BaseNokiaRpc):
    """Returns commands to replace system configuration in a Nokia format.

    Broken into multiple sub-sections / commands as there are elements under
    system we don't manage from Homer (tls certs).

    Arguments:
        data: dict provided by homer with device configuration parameters

    """

    _methods = [
        "srl_system_management",
        "srl_system_control_plane_traffic",
        "srl_system_configuration",
        "srl_aaa",
        "srl_ssh_server",
        "srl_lldp",
        "srl_system_mtu",
        "srl_hostname",
        "srl_grpc_server",
        "srl_json_rpc_server",
        "srl_dns",
        "srl_ntp",
        "srl_sflow",
        "srl_snmp",
        "srl_logging",
        "srl_net_instance_protocols",
    ]

    def srl_system_management(self) -> Iterator[NokiaRpc]:
        """Returns commands to enable openconfig RPC paths."""
        yield NokiaRpc(
            path="/system/management", config={"openconfig": {"admin-state": "enable"}}
        )

    def srl_system_control_plane_traffic(self) -> Iterator[NokiaRpc]:
        """Returns commands to configure control-plane-traffic filters/qos."""
        config = {
            "input": {
                "acl": {
                    "acl-filter": [
                        {"name": "cpm", "type": "ipv4"},
                        {"name": "cpm", "type": "ipv6"},
                    ]
                }
            }
        }
        yield NokiaRpc(path="/system/control-plane-traffic", config=config)

    def srl_system_configuration(self) -> Iterator[NokiaRpc]:
        """Returns commands to replace all system configuration section in Nokia format."""
        config = {
            "auto-checkpoint": True,
            "max-checkpoints": 64,
            "auto-save": True,
            "role": [
                # TODO: operations role probably needs write for some paths
                {"name": "wmf-ro", "rule": [{"path-reference": "/", "action": "read"}]},
                {
                    "name": "super-user",
                    "rule": [{"path-reference": "/", "action": "write"}],
                },
                {
                    "name": "operations",
                    "rule": [{"path-reference": "/", "action": "read"}],
                },
            ],
        }
        yield NokiaRpc(path="/system/configuration", config=config)

    def srl_aaa(self) -> Iterator[NokiaRpc]:
        """Returns commands to replace all AAA config in a Nokia format."""
        homer_users = self._data["users"]
        homer_users_passwords = self._data.get("users_passwords", {})
        homer_users_passwords.update(self._data["nokia_users_passwords"])
        aaa_config: dict = {
            "server-group": [{"name": "local", "type": "local"}],
            "authorization": {
                # TODO fine tune, maybe move to dedicated homer config?
                "role": [
                    {"rolename": "operations", "services": ["cli"], "superuser": False},
                    {
                        "rolename": "wmf-ro",
                        "services": ["cli", "gnmi", "json-rpc"],
                        "superuser": False,
                    },
                    {
                        "rolename": "super-user",
                        "services": ["cli", "gnmi", "json-rpc"],
                        "superuser": True,
                    },
                ]
            },
            "authentication": {
                "idle-timeout": 7200,
                "authentication-method": ["local"],
                "admin-user": {
                    "password": self._data["nokia_users_passwords"]["admin"]
                },
                "linuxadmin-user": {
                    "password": self._data["nokia_users_passwords"]["linuxadmin"]
                },
                "local-linux-users": {"disable-login": ["remote"]},
                "user": [],
            },
        }

        for user in homer_users:
            user_config = {
                "username": user["name"],
                "role": [user["class"]],
                "ssh-key": user["sshkeys"],
            }
            if homer_users_passwords.get(user["name"]):
                user_config["password"] = homer_users_passwords.get(user["name"])
            aaa_config["authentication"]["user"].append(user_config)

        yield NokiaRpc(path="/system/aaa", config=aaa_config)

    def srl_ssh_server(self) -> Iterator[NokiaRpc]:
        ssh_config = [
            {
                "name": "mgmt",
                "admin-state": "enable",
                "network-instance": "mgmt",
                "use-credentialz": True,
                "allowed-authentication-types": ["publickey"],
                "host-key": {"preserve": True},
            }
        ]
        yield NokiaRpc(path="/system/ssh-server", config=ssh_config)

    def srl_lldp(self) -> Iterator[NokiaRpc]:
        yield NokiaRpc(path="/system/lldp", config={"admin-state": "enable"})

    def srl_system_mtu(self) -> Iterator[NokiaRpc]:
        config = {
            "default-port-mtu": 9232,
            "default-l2-mtu": 9200,
            "default-ip-mtu": 9178,
        }
        yield NokiaRpc(path="/system/mtu", config=config)

    def srl_hostname(self) -> Iterator[NokiaRpc]:
        config = {"host-name": self._data["metadata"]["netbox_object"].name}
        yield NokiaRpc(path="/system/name", config=config)

    def srl_grpc_server(self) -> Iterator[NokiaRpc]:
        config = {
            "name": "mgmt",
            "admin-state": "enable",
            "tls-profile": "wmf-default",
            "default-tls-profile": True,
            "network-instance": "mgmt",
            "services": ["gnmi"],
        }
        yield NokiaRpc(path="/system/grpc-server", config=config)

    def srl_json_rpc_server(self) -> Iterator[NokiaRpc]:
        config = {
            "admin-state": "enable",
            "network-instance": [
                {
                    "name": "mgmt",
                    "http": {"admin-state": "disable"},
                    "https": {"admin-state": "enable", "tls-profile": "wmf-default"},
                }
            ],
        }
        yield NokiaRpc(path="/system/json-rpc-server", config=config)

    def srl_dns(self) -> Iterator[NokiaRpc]:
        config = {"server-list": ["10.3.0.1"], "network-instance": "mgmt"}
        yield NokiaRpc(path="/system/dns", config=config)

    def srl_ntp(self) -> Iterator[NokiaRpc]:
        config = {
            "server": [
                {"address": str(server)} for server in self._data["ntp_servers"]
            ],
            "admin-state": "enable",
            "network-instance": "mgmt",
        }
        yield NokiaRpc(path="/system/ntp", config=config)

    def srl_sflow(self) -> Iterator[NokiaRpc]:
        config = {
            "admin-state": "enable",
            "sample-rate": 1000,
            "collector": [
                {
                    "collector-id": 1,
                    "collector-address": str(
                        list(self._data["sampling"]["collectors"].values())[0]
                    ),
                    "network-instance": self._data["loopbacks"]["external"]["vrf"],
                    "source-address": self._data["loopbacks"]["external"]["4"],
                }
            ],
        }
        yield NokiaRpc(path="/system/sflow", config=config)

    def srl_snmp(self) -> Iterator[NokiaRpc]:
        config = {
            "access-group": [
                {
                    "name": "wmf-default",
                    "security-level": "no-auth-no-priv",
                    "community-entry": [
                        {
                            "name": "wmf-default",
                            "community": self._data["nokia_snmp_community"],  # hashed
                        }
                    ],
                }
            ],
            "network-instance": [{"name": "mgmt", "admin-state": "enable"}],
        }
        yield NokiaRpc(path="/system/snmp", config=config)

    def srl_logging(self) -> Iterator[NokiaRpc]:
        yield NokiaRpc(path="/system/logging/network-instance", config="mgmt")
        for target_fqdn, target_conf in self._data["syslog_servers"].items():
            config = {
                "transport": "udp",
                "remote-port": target_conf["port"],
                "facility": [
                    {
                        "facility-name": "all",
                        "priority": {"match-above": "informational"},
                    }
                ],
            }
            yield NokiaRpc(
                path=f"/system/logging/remote-server[host={target_fqdn}]",
                config=config,
            )

    def srl_net_instance_protocols(self) -> Iterator[NokiaRpc]:
        """Primarily used to define ESI segments used in MC-LAG w/EVPN"""
        if "esi_lag" not in self._data:
            return

        # Build list of eth_segments we need to define ESI ID for
        eth_segments = []
        for lag_name, lag_id in self._data["esi_lag"].items():
            lag_evpn_conf = {
                "name": lag_name.upper(),
                "admin-state": "enable",
                "esi": f"00:01:00:00:00:00:00:00:00:{lag_id}",
                "interface": [{"ethernet-interface": lag_name}],
            }
            eth_segments.append(lag_evpn_conf)

        config = {
            "evpn": {
                "ethernet-segments": {
                    "bgp-instance": [
                        {
                            "id": 1,
                            "ethernet-segment": eth_segments,
                        }
                    ]
                }
            },
            "bgp-vpn": {"bgp-instance": [{"id": 1}]},
        }
        yield NokiaRpc(path="/system/network-instance/protocols", config=config)
