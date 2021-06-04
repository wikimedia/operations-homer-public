term puppet {
    destination-address:: puppetmaster_group
    protocol:: tcp
    destination-port:: puppet
    action:: accept
}
term apt {
    destination-address:: apt_group
    protocol:: tcp
    destination-port:: HTTP HTTPS
    action:: accept
}
term webproxy {
    destination-address:: install_group
    protocol:: tcp
    destination-port:: SQUID_PROXY
    action:: accept
}
# TODO should also allow TCP, and restricted by destination
term dns {
    protocol:: udp
    destination-port:: DNS
    action:: accept
}
term ntp {
    protocol:: udp
    destination-port:: NTP
    action:: accept
}
term smtp {
    protocol:: tcp
    destination-port:: SMTP
    action:: accept
}
term icinga {
    destination-address:: alert_group
    action:: accept
}
term ldap {
    destination-address:: seaborgium serpens ldap-ro.eqiad
    protocol:: tcp
    destination-port:: LDAP_ALL
    action:: accept
}
term tftp {
    destination-address:: install_group
    protocol:: udp
    destination-port:: TFTP linux_high_ports
    action:: accept
}
term vrrp {
    protocol:: vrrp ah
    action:: accept
}
# TODO restrict to install servers?
term dhcp {
    protocol:: udp
    destination-port:: DHCP
    action:: accept
}
term neighbor_discovery {
   destination-address:: neighbor_discovery
   action:: accept
}