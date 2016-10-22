#!/bin/bash

# MANAGED BY PUPPET
# PART OF SFDC FUEL PLUGIN

LONGDATETIME=`date`

IP_ADDRESS=`/sbin/ip ro get 8.8.8.8 |  awk '(/src/) { print $7}'`
HOSTNAME="00-global-clusters-env1"
SERVICEDESC="glance1"
NOTIFICATIONTYPE="RECOVERY"
COMMENT="COMMENT"
STATE="OK"
#STATE="UNCKNOWN"
#STATE="WARNING"
#STATE="CRITICAL"


SCRIPT_NAME='/usr/lib/nagios/plugins/sfdc//sfdc_nagios.py'
CONFIG_NAME='/usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml'
LOG_NAME='./nagios_to_sfdc_sender.log'



SERVICEOUTPUT="neutron DOWN"

#LONGSERVICEOUTPUT="
#All neutron-api backends are down (DOWN, rule=last(haproxy_backend_servers[service=neutron-api,state=up])==0, current=0.00)
#Endpoint check for neutron-api is failed (DOWN, rule=last(openstack_check_api)==0, current=0.00)
#Some 5xx HTTP errors have been detected on neutron-api (WARN, rule=diff(haproxy_backend_response_5xx[backend=neutron-api])0, current=6.00)
#"


LONGSERVICEOUTPUT="
The CPU usage is too high (controller node). (CRITICAL, rule=avg(cpu_idle)=5, current=1.65, host=ic3-ctl01-scc)
No datapoint have been received over the last 60 seconds (UNKNOWN, rule=min(fs_space_percent_free[fs=/var/log])2, current=-1.00, host=ic3-ctl01-scc1)
No datapoint have been received over the last 60 seconds (UNKNOWN, rule=min(fs_space_percent_free[fs=/var/log])5, current=-1.00, host=ic3-ctl01-scc2)
No datapoint have been received over the last 60 seconds (UNKNOWN, rule=min(fs_space_percent_free[fs=/])2, current=-1.00, host=ic3-ctl01-scc3)
No datapoint have been received over the last 60 seconds (UNKNOWN, rule=min(fs_space_percent_free[fs=/])5, current=-1.00, host=ic3-ctl01-scc1)
Other related alarms:
No datapoint have been received over the last 30 seconds (UNKNOWN, rule=min(mysql_cluster_connected)==0, current=-1.00, host=ic3-ctl01-scc2)
"


#LONGSERVICEOUTPUT="
#All neutron-api backends are down (DOWN, rule=last(haproxy_backend_servers[service=neutron-api,state=up])==0, current=0.00)
#Endpoint check for neutron-api is failed (DOWN, rule=last(openstack_check_api)==0, current=0.00)
#Some 5xx HTTP errors have been detected on neutron-api (WARN, rule=diff(haproxy_backend_response_5xx[backend=neutron-api])0, current=6.00)
#"



/usr/bin/printf "%b" "Notification Type: ${NOTIFICATIONTYPE} \n State: OK\n\n Date/Time: ${LONGDATETIME} \n Host: ${HOSTNAME} (Address: ${IP_ADDRESS})\n Service: ${SERVICE} \n Additional Info:\n ${SERVICE}%5Cnno+details\n \n\n Comment: ${COMMENT}" \
| ${SCRIPT_NAME} \
                               -c  ${CONFIG_NAME} \
                               --long_date_time "$LONGDATETIME" \
                               --log_file "${LOG_NAME}" \
                               --debug \
                               --description "-" \
                               --host_name "$HOSTNAME" \
                               --service_description "$SERVICEDESC" \
                               --notification_type "$NOTIFICATIONTYPE" \
                               --state ${STATE} \
                               --service_output "${SERVICEOUTPUT}" \
                               --long_service_output "${LONGSERVICEOUTPUT}"





/usr/bin/printf "%b" "Notification Type: ${NOTIFICATIONTYPE} \n State: OK\n\n Date/Time: ${LONGDATETIME} \n Host: ${HOSTNAME} (Address: ${IP_ADDRESS})\n Service: ${SERVICE} \n Additional Info:\n ${SERVICE}%5Cnno+details\n \n\n Comment: ${COMMENT}" \
| ${SCRIPT_NAME} \
                               -c  ${CONFIG_NAME} \
                               --long_date_time "$LONGDATETIME" \
                               --description "-" \
                               --host_name "$HOSTNAME" \
                               --notification_type "$NOTIFICATIONTYPE" \
                               --state ${STATE} \
                               --debug \
                               --log_file "${LOG_NAME}"


