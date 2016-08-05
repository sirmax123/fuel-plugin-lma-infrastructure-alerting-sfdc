class lma_infrastructure_alerting_sfdc::params {
  $plugin_dir                 =  '/usr/lib/nagios/plugins/sfdc/'
  $plugin_lib_file            =  '/usr/lib/nagios/plugins/sfdc/salesforce.py'
  $plugin_file                =  '/usr/lib/nagios/plugins/sfdc/sfdc_nagios.py'
  $plugin_config_file         =  '/usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml'
  $plugin_nagios_config_file  =  '/etc/nagios3/conf.d/sfdc_commands.cfg'
  $plugin_log_file            =  '/var/log/nagios_to_sfdc.log'
  $nagios_service_name        =  'nagios3'
  $nagios_contacts_file       =  '/etc/nagios3/conf.d/sfdc_contacts.cfg'
  $nagios_commands_file       =  '/etc/nagios3/conf.d/sfdc_commands.cfg'
  $logrotate_config           =  '/etc/logrotate.d/sfdc_nagios'
}

