#!/bin/bash -x


#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#




LONGDATETIME=`date`

IP_ADDRESS=`/sbin/ip ro get 8.8.8.8 |  awk '(/src/) { print $7}'`
HOSTNAME="node-99"
SERVICEDESC="nova-super-puper-service-5"
NOTIFICATIONTYPE="RECOVERY"
COMMENT="COMMENT"
STATE="OK"
STATE="UNCKNOWN"
STATE="WARNING"
STATE="CRITICAL"

/usr/bin/printf "%b" "Notification Type: ${NOTIFICATIONTYPE} \n State: OK\n\n Date/Time: ${LONGDATETIME} \n Host: 00-global-clusters-env1 (Address: ${IP_ADDRESS})\n Service: ${SERVICE} \n Additional Info:\n ${SERVICE}%5Cnno+details\n \n\n Comment: ${COMMENT}" \
| /usr/lib/nagios/plugins/sfdc/sfdc_nagios.py \
                               -c  /usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml \
                               --long_date_time "$LONGDATETIME" \
                               --description "-" \
                               --host_name "$HOSTNAME" \
                               --service_description "$SERVICEDESC" \
                               --notification_type "$NOTIFICATIONTYPE" \
                               --state ${STATE} \
                               --debug \
                               --log_file "/var/log/nagios_to_sfdc.log"




/usr/bin/printf "%b" "Notification Type: ${NOTIFICATIONTYPE} \n State: OK\n\n Date/Time: ${LONGDATETIME} \n Host: 00-global-clusters-env1 (Address: ${IP_ADDRESS})\n Service: ${SERVICE} \n Additional Info:\n ${SERVICE}%5Cnno+details\n \n\n Comment: ${COMMENT}" \
| /usr/lib/nagios/plugins/sfdc/sfdc_nagios.py \
                               -c  /usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml \
                               --long_date_time "$LONGDATETIME" \
                               --description "-" \
                               --host_name "$HOSTNAME" \
                               --notification_type "$NOTIFICATIONTYPE" \
                               --state ${STATE} \
                               --debug \
                               --log_file "/var/log/nagios_to_sfdc.log"


