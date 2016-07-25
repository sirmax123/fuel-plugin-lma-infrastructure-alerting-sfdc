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

from argparse import ArgumentParser
from salesforce import OAuth2, Client


LOG = None

def main():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.yml')

    parser.add_argument('--description', required=True,
                           help='Description (use "-" to use stdin)' )

    parser.add_argument('--notification_type',  required=True,
                           help='Notification type (PROBLEM|RECOVERY|CUSTOM). Nagios variable - $NOTIFICATIONTYPE$" ')

    parser.add_argument('--host_name',           required=True,  help='Host name. Nagios variable - $HOSTNAME$')
    parser.add_argument('--service_description', required=False, help='Service Description. Nagios variable - $SERVICEDESC$')
    parser.add_argument('--long_date_time',      required=True,  help='Date and time. Nagios variable - $LONGDATETIME$' )

    parser.add_argument('--syslog', action='store_true', default=False,
                           help='Log to syslog')

    parser.add_argument('--debug', action='store_true', default=False,
                           help='Enable debug log level')

    parser.add_argument('--log_file', default=sys.stdout,
                           help='Log file. default: stdout. Ignored if logging configured to syslog')



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


# Read from stdin if desctiption defined as '-'
    if  args.description == '-':
        args.description = ''.join(sys.stdin.readlines())

# Notification types are mapped to priority
    priority = {
        'OK':        'Informational',
        'RECOVERY':  'Informational',
        'UNCKNOWN': 'Unknown',
        'WARNING':  'Warning',
        'CRITICAL': 'Critical',
        }


    nagios_data = {
        'notification_type': priority[str(args.notification_type).upper()],
        'description': args.description,
        'host_name': args.host_name,
        'long_date_time': args.long_date_time,
         }

    if args.service_description:
        nagios_data['service_description'] = args.service_description

    LOG.debug('Nagios data: {} '.format(nagios_data))



    with open(args.config_file) as fp:
        config = yaml.load(fp)

    if 'sfdc_organization_id' in config:
        organizationId = config['sfdc_organization_id']
    else:
        organizationId = None

    sfdc_oauth2 = OAuth2(client_id=config['sfdc_client_id'],
                         client_secret=config['sfdc_client_secret'],
                         username=config['sfdc_username'],
                         password=config['sfdc_password'],
                         auth_url=config['sfdc_auth_url'],
                         organizationId = organizationId )

    environment = config['environment']

# Alert ID shoud be uniq for env
    Alert_ID =  '{}--{}'.format(environment,args.host_name)

    if args.service_description:
        nagios_data['service_description'] = args.service_description
        Alert_ID = '{}--{}'.format(Alert_ID, args.service_description)

    LOG.debug('Alert_Id: {} '.format(Alert_ID))


    sfdc_client = Client(sfdc_oauth2)

    data = {
        'Payload__c':  json.dumps(nagios_data),
        'Alert_ID__c': Alert_ID,
        'Cloud__c':    environment,
        'Priority__c': nagios_data['notification_type']
        }

    comment_data = {
        'related_id__c':     "-1",
        'Comment__c':        json.dumps(nagios_data),
        'Alert_Id__c':       Alert_ID,
        'MOS_Alert_Name__c': "MA-0" ,
        'MosAlertId__c':     "-1",
        'Cloud__c':          environment,
        }


    try:
      new_alert = sfdc_client.create_mos_alert(data)
    except Exception as E:
       LOG.debug(E)
       sys.exit(1)

    LOG.debug('New MOS_Alert status code {} '.format(new_alert.status_code))
    LOG.debug('New MOS_Alert: {} '.format(new_alert.text))

    if (new_alert.status_code  == 400) and (new_alert.json()[0]['errorCode'] == 'DUPLICATE_VALUE'):
        # Mos Alert exists
        LOG.debug('Code: {}, Error message: {} '.format(new_alert.status_code, new_alert.text))

        # Find Alert ID
        Id = new_alert.json()[0]['message'].split(" ")[-1]
        LOG.debug('MOS_Alert_Id: {} '.format(Id))


        # Get Alert name from  current alart
        current_alert = sfdc_client.get_mos_alert(Id).json()
        comment_data['MOS_Alert_Name__c'] = current_alert['Name']
        LOG.debug('Existing MOS_Alert_Id: {} '.format(current_alert))

        # Update Alert (alert contailns LAST status)
        u = sfdc_client.update_mos_alert(id=Id, data=data)

        LOG.debug('Upate status code: {} '.format(u.status_code))

        # Add comment to updated alert
        comment_data['related_id__c'] = Id
        comment_data['MosAlertId__c'] = Id
        add_comment = sfdc_client.create_mos_alert_comment(comment_data)
        LOG.debug('Add Comment status code: {} '.format(add_comment.status_code))
        LOG.debug('Add Comment data: {} '.format(add_comment.text))
    elif  (new_alert.status_code  == 201):
        # Add commnet, because MOS_Alert is LAST data and will be overriden on update
        Id = new_alert.json()['id']
        comment_data['related_id__c'] = Id
        comment_data['MosAlertId__c'] = Id
        current_alert = sfdc_client.get_mos_alert(Id).json()
        comment_data['MOS_Alert_Name__c'] = current_alert['Name']
        add_comment = sfdc_client.create_mos_alert_comment(comment_data)
        LOG.debug('Add Comment status code: {} '.format(add_comment.status_code))
        LOG.debug('Add Comment data: {} '.format(add_comment.text))

# Serach example
#    a=sfdc_client.search("SELECT Id from Case")
#    for b  in a:
#        print(b['Id'])
#        sfdc_client.get_case(b['Id'])


#    a=sfdc_client.search("SELECT Payload__c from MOS_Alerts__c")
#    for b  in a:
#        print(b['Payload__c'])
#
#        sfdc_client.get_case(b['Id'])


if __name__ == '__main__':
    main()

