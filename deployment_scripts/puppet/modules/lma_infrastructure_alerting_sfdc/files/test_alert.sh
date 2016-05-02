/usr/bin/printf "%b" "Notification Type: RECOVERY \n State: OK\n\n Date/Time: Sun Apr 24 23:38:14 UTC 2016 \n Host: 00-global-clusters-env1 (Address: 192.168.0.2)\n Service: nova \n Additional Info:\n nova+OKAY%5Cnno+details\n \n\n Comment: " \
| /usr/lib/nagios/plugins/sfdc/sfdc_nagios.py \
-c /usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml \
--long_date_time "Sun Apr 24 23:38:14 UTC 2016" \
--description "-" \
--host_name "00-global-clusters-env1" \
--service_description "nova" \
--notification_type "RECOVERY" \
--debug 