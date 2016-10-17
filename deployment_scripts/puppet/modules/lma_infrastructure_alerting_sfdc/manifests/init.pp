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

class lma_infrastructure_alerting_sfdc (
  $auth_url,
  $client_id,
  $client_secret,
  $username,
  $password,
  $env,
  $organization_id,
  $amqp_hosts,
  $amqp_user,
  $amqp_password,
  $amqp_queue_name,
  $host_regexp,
  $log_file,
  $max_time,
  $max_attempts,
  $sleep_time,
  $plugin_dir                 =  $::lma_infrastructure_alerting_sfdc::params::plugin_dir,
  $plugin_lib_file            =  $::lma_infrastructure_alerting_sfdc::params::plugin_lib_file,
  $plugin_file                =  $::lma_infrastructure_alerting_sfdc::params::plugin_file,
  $plugin_config_file         =  $::lma_infrastructure_alerting_sfdc::params::plugin_config_file,
  $plugin_nagios_config_file  =  $::lma_infrastructure_alerting_sfdc::params::plugin_nagios_config_file,
  $plugin_log_file            =  $::lma_infrastructure_alerting_sfdc::params::plugin_log_file,
  $nagios_service_name        =  $::lma_infrastructure_alerting_sfdc::params::nagios_service_name,
  $nagios_contacts_file       =  $::lma_infrastructure_alerting_sfdc::params::nagios_contacts_file,
  $nagios_commands_file       =  $::lma_infrastructure_alerting_sfdc::params::nagios_commands_file,
  $logrotate_config           =  $::lma_infrastructure_alerting_sfdc::params::logrotate_config,

) inherits lma_infrastructure_alerting_sfdc::params {

  notify {'lma_infrastructure_alerting_sfdc start': }

  validate_string($auth_url, 
                  $client_id, 
                  $client_secret,
                  $username,
                  $password,
                  $env,
                  $organization_id,
                  $amqp_hosts,
                  $amqp_user,
                  $amqp_password,
                  $amqp_queue_name,
                  $host_regexp,
                  $log_file,
                  $max_time,
                  $max_attempts,
                  $sleep_time,
                  $plugin_dir,
                  $plugin_lib_file,
                  $plugin_file,
                  $plugin_config_file,
                  $plugin_nagios_config_file,
                  $plugin_log_file,
                  $nagios_service_name,
                  $nagios_contacts_file,
                  $nagios_commands_file,
                  $logrotate_config)

#  service { "${nagios_service_name}":
#      ensure => running,
#      enable => true,
#    }

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
    "${plugin_daemon_file}" => {
      source => 'puppet:///modules/lma_infrastructure_alerting_sfdc/sfdc_sender.py',
      mode   => '0755',
    },

  }

  $file_defaults = {
    ensure => 'file',
    owner => 'nagios',
    group => 'nagios',
    mode  => '0644',
#    notify => Service[$nagios_service_name],
  }

  create_resources(file, $files, $file_defaults)


  file { '/etc/init/sfdc_sender.conf':
      ensure  => file,
      mode    => '0700',
      owner   => 'root',
      group   => 'root',
      content => template('lma_infrastructure_alerting_sfdc/sfdc_sender.conf.erb'),
    } ->

  package { $packages: ensure => 'installed' } ->


  service { "sfdc_sender":
      ensure => running,
      enable => true,
    }



  notify {'lma_infrastructure_alerting_sfdc end': }
}
