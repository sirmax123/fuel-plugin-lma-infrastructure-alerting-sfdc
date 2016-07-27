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
from salesforce import OAuth2, Client
from datetime import datetime


LOG = None
DELTA_SECONDS=300

def main():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.yml')

    parser.add_argument('--description', required=True,
                           help='Description (use "-" to use stdin)' )

    parser.add_argument('--notification_type',  required=True,
                           help='Notification type (PROBLEM|RECOVERY|CUSTOM). Nagios variable - $NOTIFICATIONTYPE$" ')

    parser.add_argument('--state',  required=True,
                           help='Service ot Host (OK|WARNING|CRITICAL|UNCKNOWN). Nagios variable - $SERVICESTATE$" or $HOSTSTATE$ ')

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

# state are mapped to priority 
    state = {
        'OK':       '060 Informational',
        'UNKNOWN': '070 Unknown',
        'WARNING':  '080 Warning',
        'CRITICAL': '090 Critical',
        }


    nagios_data = {
        'state': state[str(args.state).upper()],
        'notification_type': args.notification_type,
        'description': args.description,
        'host_name': args.host_name,
        'long_date_time': args.long_date_time,
         }

    if args.service_description:
        nagios_data['service_description'] = args.service_description
    else:
        nagios_data['service_description'] = ''

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



# Workaround for sort order. 
# SFDC allow to use only one field for sort, so  it is not possible to have CRITICAL items frist sorted by time, then WARN sorted by time  etc
# So  I use field which contains some kind of anti-date, years letft before 2100 + monthes left before end of the year +  days before ent of the month etc.
# In  this way I have string which  can be sorted in correct way
#    Y=2100-int(datetime.strftime(datetime.now(), "%Y"))
#    m=12-int(datetime.strftime(datetime.now(), "%m"))
#    d=31-int(datetime.strftime(datetime.now(), "%d"))
#    H=24-int(datetime.strftime(datetime.now(), "%H"))
#    M=60-int(datetime.strftime(datetime.now(), "%M"))
#    S=60-int(datetime.strftime(datetime.now(), "%S"))
#
#    sort_marker='{}{}{}{}{}{}'.format(str(Y).zfill(2), str(m).zfill(2), str(d).zfill(2), str(H).zfill(2), str(M).zfill(2), str(S).zfill(2) )
#

    payload = {
        'notification_type': args.notification_type,
        'description':       args.description,
        'long_date_time':    args.long_date_time,
         }

    data = {
        'Payload__c':  json.dumps(payload),
        'Alert_ID__c': Alert_ID,
        'Cloud__c':    environment,
        'Priority__c': nagios_data['state'],
        'Host__c':     nagios_data['host_name'],
        'Service__c':  nagios_data['service_description'],

#        'sort_marker__c': sort_marker,
        }

    comment_data = {
        'related_id__c':     "-1",
        'Comment__c':        json.dumps(nagios_data),
        'Alert_Id__c':       Alert_ID,
        'MOS_Alert_Name__c': "MA-0" ,
        'MosAlertId__c':     "-1",
        'Cloud__c':          environment,
        'Priority__c':       nagios_data['state'],
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


        # Get Alert name from  current alert
        current_alert = sfdc_client.get_mos_alert(Id).json()
        LOG.debug(json.dumps(current_alert,sort_keys=True, indent=4))

        # We have current alert and need to change status. If this alert is older N days 
        # need to update it, if newer - 


        comment_data['MOS_Alert_Name__c'] = current_alert['Name']
        LOG.debug('Existing MOS_Alert_Id: {} '.format(current_alert))


        LastModifiedDate=current_alert['LastModifiedDate']
        LOG.debug(LastModifiedDate)
        Now=datetime.now().replace(tzinfo=None)
        delta = Now - dateutil.parser.parse(LastModifiedDate).replace(tzinfo=None)
        #print(dateutil.parser.parse(LastModifiedDate))
        #print(delta.seconds)

        if (delta.seconds > DELTA_SECONDS):
          # Old alert is outdated
          new_data = {
            'Alert_Id__c': '{}_closed_at_{}'.format(current_alert['Alert_ID__c'],datetime.strftime(datetime.now(), "%Y.%m.%d-%H:%M:%S")),
            'Priority__c': '000 OUTDATED',
          }
          u = sfdc_client.update_mos_alert(id=Id, data=new_data)
          LOG.debug('Upate status code: {} '.format(u.status_code))
          LOG.debug('Upate content: {} '.format(u.content))
          LOG.debug('Upate headers: {} '.format(u.headers))
 
          # Try to create new alert again 
          try:
            new_alert = sfdc_client.create_mos_alert(data)
          except Exception as E:
            LOG.debug(E)
            sys.exit(1)
          else:
            Id = new_alert.json()['id']
            comment_data['related_id__c'] = Id
            comment_data['MosAlertId__c'] = Id
            current_alert = sfdc_client.get_mos_alert(Id).json()
            comment_data['MOS_Alert_Name__c'] = current_alert['Name']
            add_comment = sfdc_client.create_mos_alert_comment(comment_data)
            LOG.debug('Add Comment status code: {} '.format(add_comment.status_code))
            LOG.debug('Add Comment data: {} '.format(add_comment.text))

        else:

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
    else:
        LOG.debug("Unexpected error: Alert was not created (code !=201) and alert does not exist (code != 400)")
        sys.exit(1)

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

