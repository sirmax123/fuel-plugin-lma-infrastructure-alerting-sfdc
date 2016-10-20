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
from salesforce import OAuth2, Client
import socket
import sys
import time
import urllib3
import yaml

urllib3.disable_warnings()
LOG = None


def send_to_sfdc(nagios_data, config_file, LOG):
    with open(config_file) as fp:
        config = yaml.safe_load(fp)
        amqp_hosts = config['amqp_hosts'].split(',')
        amqp_user = config['amqp_user']
        amqp_password = config['amqp_password']
        amqp_queue_name = config['amqp_queue_name']
        host_regexp = config['host_regexp']
        max_attempts = int(config['max_attempts'])
        sleep_time = int(config['sleep_time'])
        environment = config['environment']
        sfdc_client_id = config['sfdc_client_id']
        sfdc_client_secret = config['sfdc_client_secret']
        sfdc_username = config['sfdc_username']
        sfdc_password = config['sfdc_password']
        sfdc_auth_url = config['sfdc_auth_url']
        sfdc_organization_id = config['sfdc_organization_id']

    sfdc_oauth2 = OAuth2(client_id=sfdc_client_id,
                         client_secret=sfdc_client_secret,
                         username=sfdc_username,
                         password=sfdc_password,
                         auth_url=sfdc_auth_url,
                         organizationId=sfdc_organization_id)

    sfdc_client = Client(sfdc_oauth2)

    payload = {
        'long_date_time': nagios_data['long_date_time']
    }

    Alert_ID = environment
    Subject = ''

    if nagios_data['service_description']:
        Alert_ID = '{}--{}'.format(Alert_ID, nagios_data['service_description'])
        Subject = nagios_data['service_description']
        payload['service'] = nagios_data['service_description']

    if nagios_data['affected_hosts']:
        Subject = '{}  {}'.format(Subject, nagios_data['affected_hosts'][0])
    else:
        Subject = '{}  {}'.format(Subject, nagios_data['host_name'])

    Alert_ID = '{}--{}'.format(Alert_ID, nagios_data['host_name'])

    if nagios_data['long_service_output']:
        payload['description'] = nagios_data['long_service_output']

    alert_data = {
        'IsMosAlert__c':     'true',
        'Description':       json.dumps(payload, sort_keys=True, indent=4),
        'Alert_ID__c':       Alert_ID,
        'Subject':           Subject,
        'Environment2__c':   environment,
        'Alert_Priority__c': nagios_data['state'],
        'Alert_Host__c':     nagios_data['host_name'],
        'Alert_Service__c':  nagios_data['service_description']
        }

    feed_data_body = {
        'Description':    json.dumps(payload, sort_keys=True, indent=4),
        'Alert_Id':       Alert_ID,
        'Cloud_ID':       environment,
        'Alert_Priority': nagios_data['state'],
        'Status':         'New',
        }

    LOG.info(json.dumps(alert_data, sort_keys=True, indent=4))

    try:
        new_case = sfdc_client.create_case(alert_data)
        LOG.info('New Caset status code: {} '.format(new_case.status_code))
        LOG.info('New Case data: {} '.format(new_case.text))

        #  If Case exists
        if (new_case.status_code == 400) and (new_case.json()[0]['errorCode'] == 'DUPLICATE_VALUE'):
            LOG.info('Code: {}, Error message: {} '.format(new_case.status_code, new_case.text))
            # Find Case ID
            ExistingCaseId = new_case.json()[0]['message'].split(' ')[-1]

            u = sfdc_client.update_case(id=ExistingCaseId, data=alert_data)
            LOG.info('Upate status code: {} '.format(u.status_code))

            feeditem_data = {
                    'ParentId':    ExistingCaseId,
                    'Visibility': 'AllUsers',
                    'Body':        json.dumps(feed_data_body, sort_keys=True, indent=4)
            }

            LOG.info('FeedItem Data: {}'.format(json.dumps(feeditem_data, sort_keys=True, indent=4)))
            add_feed_item = sfdc_client.create_feeditem(feeditem_data)
            LOG.info('Add FeedItem status code: {} \n Add FeedItem reply: {} '.format(add_feed_item.status_code, add_feed_item.text))
            return
        # Else If Case did not exist before and was just created
        elif (new_case.status_code == 201):
            LOG.info('Case was just created')
            # Add commnet, because Case head should conains  LAST data  overriden on any update
            CaseId = new_case.json()['id']
            feeditem_data = {
               'ParentId':   CaseId,
               'Visibility': 'AllUsers',
               'Body': json.dumps(feed_data_body, sort_keys=True, indent=4),
            }
            LOG.info('FeedItem Data: {}'.format(json.dumps(feeditem_data, sort_keys=True, indent=4)))
            add_feed_item = sfdc_client.create_feeditem(feeditem_data)
            LOG.info('Add FeedItem status code: {} \n Add FeedItem reply: {} '.format(add_feed_item.status_code, add_feed_item.text))
            return
        else:
            LOG.info('Unexpected error: Case was not created (code !=201) and Case does not exist (code != 400), raising exeption!')
            raise requests.exceptions.ConnectionError

    except requests.exceptions.ConnectionError as E:
        LOG.info(E)

        LOG.info('Unexpected error: Case was not created (code !=201) and Case does not exist (code != 400) or connection error')
        new_body = json.loads(str(body))
        LOG.info('Failed to sent, updating message:  \n {}  \n '.format(json.dumps(new_body, sort_keys=True, indent=4)))


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

    logging.getLogger("pika").setLevel(logging.INFO)

# parse config file
    with open(args.config_file) as fp:
        config = yaml.safe_load(fp)
        amqp_hosts = config['amqp_hosts'].split(',')
        amqp_user = config['amqp_user']
        amqp_password = config['amqp_password']
        amqp_queue_name = config['amqp_queue_name']
        host_regexp = config['host_regexp']
        max_attempts = int(config['max_attempts'])
        sleep_time = int(config['sleep_time'])
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
                send_to_sfdc(nagios_data=nagios_data, config_file=args.config_file, LOG=LOG)

                LOG.info('Exiting with code = 1')
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
