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


$lma_infrastructure_alerting = hiera_hash('lma_infrastructure_alerting', {})


$plugin = hiera('lma_infrastructure_alerting_sfdc')
$rabbit = hiera('rabbit')

$sfdc_auth_url = $plugin['sfdc_auth_url']


$sfdc_client_id = $plugin['sfdc_client_id']
$sfdc_client_secret = $plugin['sfdc_client_secret']

$sfdc_username = $plugin['sfdc_username']
$sfdc_password = $plugin['sfdc_password']

$sfdc_environment = $plugin['environment']
$sfdc_organization_id = $plugin['sfdc_organization_id']


$sfdc_amqp_hosts = hiera('amqp_hosts')


$sfdc_amqp_user     = $rabbit['user']
$sfdc_amqp_password = $rabbit['password']

$sfdc_amqp_queue_name = $plugin['amqp_queue_name']



$sfdc_host_regexp  = $plugin['host_regexp']
$sfdc_log_file     = $plugin['plugin_log_file']
$sfdc_max_time     = $plugin['max_time']
$sfdc_max_attempts = $plugin['max_attempts']
$sfdc_sleep_time   = $plugin['sleep_time']


class { 'lma_infrastructure_alerting_sfdc':
  auth_url        =>  $sfdc_auth_url,
  client_id       =>  $sfdc_client_id,
  client_secret   =>  $sfdc_client_secret,
  username        =>  $sfdc_username,
  password        =>  $sfdc_password,
  env             =>  $sfdc_environment,
  organization_id =>  $sfdc_organization_id,
  amqp_hosts      =>  $sfdc_amqp_hosts,
  amqp_user       =>  $sfdc_amqp_user,
  amqp_password   =>  $sfdc_amqp_password,
  amqp_queue_name =>  $sfdc_amqp_queue_name,
  host_regexp     =>  $sfdc_host_regexp,
  log_file        =>  $sfdc_log_file,
  max_time        =>  $sfdc_max_time,
  max_attempts    =>  $sfdc_max_attempts,
  sleep_time      =>  $sfdc_sleep_time,
}

