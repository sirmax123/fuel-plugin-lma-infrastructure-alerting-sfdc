#    Copyright 2015 Mirantis, Inc.
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

class lma_infrastructure_alerting_sfdc (
  $auth_url,
  $client_id,
  $client_secret,
  $username,
  $password,
  $env,
  $organization_id,
  $plugin_dir                 =  '/usr/lib/nagios/plugins/sfdc/',
  $plugin_lib_file            =  '/usr/lib/nagios/plugins/sfdc/salesforce.py',
  $plugin_file                =  '/usr/lib/nagios/plugins/sfdc/sfdc_nagios.py',
  $plugin_config_file         =  '/usr/lib/nagios/plugins/sfdc/sfdc_nagios.yaml',
  $plugin_nagios_config_file  =  '/etc/nagios3/conf.d/sfdc_commands.cfg',
  $plugin_log_file            =  '/var/log/nagios_to_sfdc.log',
  $nagios_service_name        =  'nagios3',
  $nagios_contacts_file       =  '/etc/nagios3/conf.d/sfdc_contacts.cfg',
  $nagios_commands_file       =  '/etc/nagios3/conf.d/sfdc_commands.cfg',
  $logrotate_config           =  '/etc/logrotate.d/sfdc_nagios'

)  {

  notify {'lma_infrastructure_alerting_sfdc start': }

  service { $nagios_service_name:
      ensure => running,
      enable => true,
    }

  $files = {
    "${plugin_dir}" => {
      ensure => 'directory',
      owner  => 'nagios',},
    "${plugin_lib_file}" => {
      source => 'puppet:///modules/lma_infrastructure_alerting_sfdc/salesforce.py',
      mode   => '0755',
    },
    "${plugin_dir}test_alert.sh" => {
      content => template('lma_infrastructure_alerting_sfdc/test_alert.sh.erb'),
      mode    => '0755',
    },
    "${plugin_file}" => {
      source => 'puppet:///modules/lma_infrastructure_alerting_sfdc/sfdc_nagios.py',
      mode   => '0755',
    },
    "${plugin_config_file}" => {
      content => template('lma_infrastructure_alerting_sfdc/sfdc_nagios.yaml.erb'),
    },
    "${logrotate_config}" => {
      content => template('lma_infrastructure_alerting_sfdc/sfdc_nagios.yaml.erb'),
      owner   => 'root',
    },
    "${nagios_contacts_file}" => {
      source => 'puppet:///modules/lma_infrastructure_alerting_sfdc/sfdc_contacts.cfg',
    },
    "${plugin_log_file}" => {
    },
    "${nagios_commands_file}" => {
      content => template('lma_infrastructure_alerting_sfdc/sfdc_commands.cfg.erb'),
    },
  }

  $file_defaults = {
    ensure => 'file',
    owner => 'nagios',
    group => 'nagios',
    mode  => '0644',
    notify => Service[$nagios_service_name],
  }

  create_resources(file, $files, $file_defaults)

  notify {'lma_infrastructure_alerting_sfdc end': }
}
