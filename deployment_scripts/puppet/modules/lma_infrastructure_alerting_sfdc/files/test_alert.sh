#!/bin/bash -x

LONGDATETIME=`date`

IP_ADDRESS=`/sbin/ip ro get 8.8.8.8 |  awk '(/src/) { print $7}'`
HOSTNAME="3"
SERVICEDESC="nova"
NOTIFICATIONTYPE="RECOVERY"
COMMENT="COMMENT"

/usr/bin/printf "%b" "Notification Type: ${NOTIFICATIONTYPE} \n State: OK\n\n Date/Time: ${LONGDATETIME} \n Host: 00-global-clusters-env1 (Address: ${IP_ADDRESS})\n Service: ${SERVICE} \n Additional Info:\n ${SERVICE}%5Cnno+details\n \n\n Comment: ${COMMENT}" \
| /usr/lib/nagios/plugins/sfdc/sfdc_nagios.py \
                               -c  /usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml \
                               --long_date_time "$LONGDATETIME" \
                               --description "-" \
                               --host_name "$HOSTNAME" \
                               --service_description "$SERVICEDESC" \
                               --notification_type "$NOTIFICATIONTYPE" \
                               --debug \
                               --log_file "/var/log/nagios_to_sfdc.log"








