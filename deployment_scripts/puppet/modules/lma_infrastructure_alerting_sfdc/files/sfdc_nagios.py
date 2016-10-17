#!/usr/bin/python
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
# Configure the Nagios server with the CGI service for passive checks.
# Configure virtual hosts for monitoring the clusters of global services and nodes
#



import logging
import os
import sys
import yaml
import json
# import shutil
import socket
import dateutil.parser
from argparse import ArgumentParser
from datetime import datetime
import pika
import re
import time


LOG = None
DELTA_SECONDS=3000000000
#DELTA_SECONDS=1

def main():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.yml')


    parser.add_argument('--syslog', action='store_true', default=False,
                           help='Log to syslog')

    parser.add_argument('--debug', action='store_true', default=False,
                           help='Enable debug log level')

    parser.add_argument('--log_file', default=sys.stdout,
                           help='Log file. default: stdout. Ignored if logging configured to syslog')


    parser.add_argument('--description', required=True,
                           help='Description (use "-" to use stdin)' )

    parser.add_argument('--notification_type',  required=True,
                           help='Notification type (PROBLEM|RECOVERY|CUSTOM). Nagios variable - $NOTIFICATIONTYPE$" ')

    parser.add_argument('--state',  required=True,
                           help='Service ot Host (OK|WARNING|CRITICAL|UNCKNOWN). Nagios variable - $SERVICESTATE$" or $HOSTSTATE$ ')

    parser.add_argument('--host_name',           required=True,  help='Host name. Nagios variable - $HOSTNAME$')
    parser.add_argument('--service_description', required=False, help='Service Description. Nagios variable - $SERVICEDESC$')
    parser.add_argument('--long_date_time',      required=True,  help='Date and time. Nagios variable - $LONGDATETIME$' )

    parser.add_argument('--service_output',  required=False, help='Service Output. Nagios variable - $SERVICEOUTPUT$')

    parser.add_argument('--long_service_output', required=False, help='Service Long Output. Nagios variable - $$LONGSERVICEOUTPUT$')



    args = parser.parse_args()

    LOG = logging.getLogger()
    if args.syslog:
        handler = logging.SysLogHandler()
    elif (args.log_file != sys.stdout ):
        handler = logging.FileHandler(args.log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)

    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    formatter = logging.Formatter(
        '{} nagios_to_sfdc %(asctime)s %(process)d %(levelname)s %(name)s '
        '[-] %(message)s'.format(socket.getfqdn()),
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler.setFormatter(formatter)
    LOG.setLevel(log_level)
    LOG.addHandler(handler)



# parse config file
    with open(args.config_file) as fp:
        config = yaml.load(fp)
        amqp_host = config['amqp_host']
        amqp_port = int(config['amqp_port'])
        amqp_user = config['amqp_user']
        amqp_password = config['amqp_password']
        amqp_queue_name = config['amqp_queue_name']
        host_regexp = config['host_regexp']

# Read from stdin if desctiption defined as '-'
    if  args.description == '-':
        args.description = ''.join(sys.stdin.readlines())

# state are mapped to priority 
    state = {
        'OK':       '060 Informational',
        'UNKNOWN':  '070 Unknown',
        'WARNING':  '080 Warning',
        'CRITICAL': '090 Critical',
        }

    nagios_data = {
        'state':             state[str(args.state).upper()],
        'notification_type': args.notification_type,
        'description':       args.description,
        'host_name':         args.host_name,
        'long_date_time':    args.long_date_time,
    }

    if args.service_description:
        nagios_data['service_description'] = args.service_description



    if args.service_description:
        nagios_data['service_description'] = args.service_description
    else:
        nagios_data['service_description'] = ''

    if args.service_output:
        nagios_data['service_output'] = args.service_output
    else:
        nagios_data['service_output'] = ''

    if args.long_service_output:
        nagios_data['long_service_output'] = args.long_service_output
        nagios_data['affected_hosts'] = list(set(re.findall(host_regexp, nagios_data['long_service_output'])))
    else:
        nagios_data['long_service_output'] = ''
        nagios_data['affected_hosts'] = []



    nagios_data['publishing_time'] = int(time.time())
    nagios_data['sfdc_attempts'] = 0

    LOG.debug('Nagios data: \n {} \n '.format(json.dumps(nagios_data,sort_keys=True, indent=4)))


#Alert Payloadb should be in the first comment of the alert.
#Alert name: rabbitmq-queue-warning
#Service: rabbitmq
#Rule: rule=avg(rabbitmq_messages)=200, current=200.67
#Date/Time: Fri Sept 9 01:20:27 UTC 2016


    credentials = pika.PlainCredentials(amqp_user, amqp_password)
    pareameters = pika.ConnectionParameters(amqp_host, amqp_port, '/', credentials)

    try:
        connection = pika.BlockingConnection(pareameters)
    except Exception as E:
        LOG.debug(E)
        sys.exit(1)

    properties=pika.BasicProperties(delivery_mode = 2,)

    channel = connection.channel()
    channel.queue_declare(queue=amqp_queue_name, durable=True)


    channel.basic_publish(exchange='',
                      routing_key = amqp_queue_name,
                      body = json.dumps(nagios_data),
                      properties = properties)

    connection.close()






if __name__ == '__main__':
    main()

