#!/usr/bin/python

from argparse import ArgumentParser
from datetime import datetime
import dateutil.parser
import itertools
import json
import logging
import os
import pika
import re
import requests
from salesforce import OAuth2, Client, send_to_sfdc
import socket
import sys
import time
import urllib3
import yaml

urllib3.disable_warnings()
LOG = None


def main():

    LOG = logging.getLogger()
    if args.syslog:
        handler = logging.SysLogHandler()
    elif (args.log_file != sys.stdout):
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

    logging.getLogger("pika").setLevel(logging.CRITICAL)
    LOG.info('Args = {} '.format(args))

# parse config file
    with open(args.config_file) as fp:
        config = yaml.safe_load(fp)
        amqp_hosts = config['amqp_hosts'].split(',')
        amqp_user = config['amqp_user']
        amqp_password = config['amqp_password']
        amqp_queue_name = config['amqp_queue_name']
        host_regexp = config['host_regexp']
        max_attempts = int(config['max_attempts_rabbit'])
        sleep_time = int(config['sleep_time_rabbit'])
        environment = config['environment']
        sfdc_client_id = config['sfdc_client_id']
        sfdc_client_secret = config['sfdc_client_secret']
        sfdc_username = config['sfdc_username']
        sfdc_password = config['sfdc_password']
        sfdc_auth_url = config['sfdc_auth_url']
        sfdc_organization_id = config['sfdc_organization_id']

# Read from stdin if desctiption defined as '-'
    if args.description == '-':
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

    LOG.info('Nagios data: \n {} \n '.format(json.dumps(nagios_data, sort_keys=True, indent=4)))

    for amqp_conn_string in itertools.cycle(amqp_hosts):

        amqp_host = amqp_conn_string.split(':')[0].strip()
        amqp_port = int(amqp_conn_string.split(':')[1].strip())

        credentials = pika.PlainCredentials(amqp_user, amqp_password)
        pareameters = pika.ConnectionParameters(amqp_host, amqp_port, '/', credentials)

        try:
            connection = pika.BlockingConnection(pareameters)

            properties = pika.BasicProperties(delivery_mode=2,)

            channel = connection.channel()
            channel.queue_declare(queue=amqp_queue_name, durable=True)

            channel.basic_publish(exchange='',
                                  routing_key=amqp_queue_name,
                                  body=json.dumps(nagios_data),
                                  properties=properties)

            connection.close()
            LOG.info('Sent to  amqp_conn_string = {},  amqp_host = {}, amqp_port = {} '.format(amqp_conn_string, amqp_host, amqp_port))
            LOG.info('Exiting with code = 0')
            sys.exit(0)
        except Exception as E:
            LOG.info('Failed to sent. max_attempts  = {}, amqp_conn_string = {},  amqp_host = {}, amqp_port = {} '.format(max_attempts, amqp_conn_string, amqp_host, amqp_port))
            LOG.info(E)

            if max_attempts <= 0:
                LOG.info('Failed to sent. max_attempts  = {} '.format(max_attempts))
                LOG.info('Trying to send to SFDC w/o rabbit.')

                sfdc_oauth2 = OAuth2(client_id=sfdc_client_id,
                                     client_secret=sfdc_client_secret,
                                     username=sfdc_username,
                                     password=sfdc_password,
                                     auth_url=sfdc_auth_url,
                                     organizationId=sfdc_organization_id)

                sfdc_client = Client(sfdc_oauth2)

                if send_to_sfdc(nagios_data=nagios_data,  sfdc_client=sfdc_client, environment=environment):
                    LOG.info('Exiting with code = {}'.format('True'))
                    sys.exit(0)
                else:
                    LOG.info('Exiting with code = {}'.format('False'))
                    sys.exit(1)
            else:
                max_attempts = max_attempts - 1
                LOG.info('Starting sleep: sleep_time = {}, now = {} '.format(sleep_time, int(time.time())))
                time.sleep(sleep_time)
                LOG.info('Sleep Finished: sleep_time = {}, now = {} '.format(sleep_time, int(time.time())))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.yml')

    parser.add_argument('--syslog', action='store_true', default=False,
                        help='Log to syslog')

    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug log level')

    parser.add_argument('--log_file', default=sys.stdout,
                        help='Log file. default: stdout. Ignored if logging configured to syslog')

    parser.add_argument('--description', required=True,
                        help="Description (use '-' to use stdin)")

    parser.add_argument('--notification_type',  required=True,
                        help='Notification type (PROBLEM|RECOVERY|CUSTOM). Nagios variable - $NOTIFICATIONTYPE$')

    parser.add_argument('--state',  required=True,
                        help='Service ot Host (OK|WARNING|CRITICAL|UNCKNOWN). Nagios variable - $SERVICESTATE$ or $HOSTSTATE$ ')

    parser.add_argument('--host_name',           required=True,  help='Host name. Nagios variable - $HOSTNAME$')
    parser.add_argument('--service_description', required=False, help='Service Description. Nagios variable - $SERVICEDESC$')
    parser.add_argument('--long_date_time',      required=True,  help='Date and time. Nagios variable - $LONGDATETIME$')

    parser.add_argument('--service_output',  required=False, help='Service Output. Nagios variable - $SERVICEOUTPUT$')

    parser.add_argument('--long_service_output', required=False, help='Service Long Output. Nagios variable - $$LONGSERVICEOUTPUT$')
    args = parser.parse_args()

    main()
