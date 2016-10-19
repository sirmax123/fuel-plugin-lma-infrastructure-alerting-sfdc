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

class lma_infrastructure_alerting_sfdc::params {
  $plugin_dir                 =  '/usr/lib/nagios/plugins/sfdc/'
  $plugin_lib_file            =  '/usr/lib/nagios/plugins/sfdc/salesforce.py'
  $plugin_file                =  '/usr/lib/nagios/plugins/sfdc/sfdc_nagios.py'
  $plugin_daemon_file         =  '/usr/lib/nagios/plugins/sfdc/sfdc_sender.py'
  $plugin_config_file         =  '/usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml'
  $plugin_nagios_config_file  =  '/etc/nagios3/conf.d/sfdc_commands.cfg'
  $plugin_log_file            =  '/var/log/nagios_to_sfdc.log'
  $nagios_service_name        =  'nagios3'
  $nagios_contacts_file       =  '/etc/nagios3/conf.d/sfdc_contacts.cfg'
  $nagios_commands_file       =  '/etc/nagios3/conf.d/sfdc_commands.cfg'
  $logrotate_config           =  '/etc/logrotate.d/sfdc_nagios'
  $packages                   =  [ 'python-pika' ]
  $queue_name                 =  'sfdc_queue'
}

