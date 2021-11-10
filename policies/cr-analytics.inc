#include 'cr-common-infrastructure.inc'
term analytics-subnets {
    destination-address:: analytics-subnets
    action:: accept
}
term analytics-publicIP {
    destination-address:: cloudservices1004
                          install1003
                          labstore1006
                          labstore1007
    action:: accept
}
term graphite {
    destination-address:: graphite_group
    protocol:: tcp udp
    destination-port:: graphite
    action:: accept
}
term statsd {
    destination-address:: graphite_group
    protocol:: udp
    destination-port:: STATSD
    action:: accept
}
term mysql-dbstore {
    destination-address:: dbstore_group
    protocol:: tcp
    destination-port:: mysql-wiki-replicas mysql-analytics-staging
    action:: accept
}
term mysql-sqoop {
    destination-address:: clouddb1021
    protocol:: tcp
    destination-port:: mysql-wiki-replicas
    action:: accept
}
# Temporarily added transferpy to the term below
# in order to to facilitate a transfer.py operation: T295312
term mysql-replica {
    destination-address:: db1108
    protocol:: tcp
    destination-port:: mysql-analytics-replicas transferpy
    action:: accept
}
term mysql-dbproxy {
    destination-address:: dbproxy1013 dbproxy1015
    protocol:: tcp
    destination-port:: mySQL
    action:: accept
}
term ssh {
    destination-address:: sodium
    protocol:: tcp
    destination-port:: SSH
    action:: accept
}
term rsync-http-https {
    destination-address:: sodium
                          mwlog_group
    protocol:: tcp
    destination-port:: RSYNC HTTP HTTPS
    action:: accept
}
term return-tcp {
    protocol:: tcp
    option:: tcp-established
    action:: accept
}
term kafka {
    destination-address:: kafka-jumbo_group
                          kafka-main_group
                          kafka-logging_group
    protocol:: tcp
    destination-port:: kafka kafkaTLS
    action:: accept
}
term archiva {
    destination-address:: archiva_group
    protocol:: tcp
    destination-port:: RSYNC HTTP HTTPS
    action:: accept
}
term gerrit {
    destination-address:: gerrit_group
                          gerrit.wikimedia.org
                          gerrit-replica.wikimedia.org
    protocol:: tcp
    destination-port:: HTTPS gerritSSH
    action:: accept
}
term bacula {
    destination-address:: backup_group
    protocol:: tcp udp
    destination-port:: bacula
    action:: accept
}
term aqs {
    destination-address:: aqs_group
    protocol:: tcp
    destination-port:: AQS
    action:: accept
}
term wdqs {
    destination-address:: wdqs_group wdqs.svc.eqiad
    protocol:: tcp
    destination-port:: WDQS
    action:: accept
}
term icmp {
    protocol:: icmp
    action:: accept
}
term icmp6 {
    protocol:: icmpv6
    action:: accept
}
term druid {
    destination-address:: druid_group
    protocol:: tcp
    destination-port:: druid
    action:: accept
}
term syslog {
    comment:: "T177821"
    destination-address:: centrallog_group
    protocol:: udp
    destination-port:: SYSLOG
    action:: accept
}
term syslog-tls {
    comment:: "T177821"
    destination-address:: centrallog_group
    protocol:: tcp
    destination-port:: SYSLOGTLS
    action:: accept
}
term debmonitor {
    comment:: "T261489"
    destination-address:: debmonitor_group
    protocol:: tcp
    destination-port:: HTTPS
    action:: accept
}
term scap {
    destination-address:: deploy_group
    protocol:: tcp
    destination-port:: HTTP HTTPS
    action:: accept
}
term swift {
    destination-address:: ms-fe.svc.codfw
                          ms-fe.svc.eqiad
                          thanos-swift.svc.codfw
                          thanos-swift.svc.eqiad
    protocol:: tcp
    destination-port:: HTTPS
    action:: accept
}
term schema {
    destination-address:: schema.svc.codfw
                          schema.svc.eqiad
    protocol:: tcp
    destination-port:: HTTPS
    action:: accept
}
term kerberos {
    destination-address:: krb_group
    protocol:: tcp udp
    destination-port:: kerberos kerberos-pwd
    action:: accept
}
term eventgate-analytics {
    destination-address:: eventgate-analytics.svc.eqiad
                          eventgate-analytics.svc.codfw
    protocol:: tcp
    destination-port:: eventgate-analytics
    action:: accept
}
term eventgate-main {
    destination-address:: eventgate-main.svc.eqiad
                          eventgate-main.svc.codfw
    protocol:: tcp
    destination-port:: eventgate-main
    action:: accept
}
term eventgate-logging-ext {
    destination-address:: eventgate-logging-external.svc.eqiad
                          eventgate-logging-external.svc.codfw
    protocol:: tcp
    destination-port:: eventgate-logging-external
    action:: accept
}
term eventgate-analytics-ext {
    destination-address:: eventgate-analytics-external.svc.eqiad
                          eventgate-analytics-external.svc.codfw
    protocol:: tcp
    destination-port:: eventgate-analytics-external
    action:: accept
}
term idp {
    destination-address:: idp_group
    protocol:: tcp
    destination-port:: HTTPS
    action:: accept
}
term mediawiki-api {
    comment:: "T274951"
    destination-address:: api.svc.eqiad api.svc.codfw
    protocol:: tcp
    destination-port:: HTTP HTTPS
    action:: accept
}
term pki {
    destination-address:: pki_group
    protocol:: tcp
    destination-port:: HTTP HTTPS
    action:: accept
}
term default {
    action:: deny
}