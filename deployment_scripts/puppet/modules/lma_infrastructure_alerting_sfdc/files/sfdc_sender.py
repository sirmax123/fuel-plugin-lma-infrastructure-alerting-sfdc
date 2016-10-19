#!/usr/bin/env python

import requests
import time
import pika
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
from functools import partial
import itertools


def callback2(ch, method, properties, body, config, LOG, sfdc_client, channel):

    LOG.info('Starting ... ')
    environment = config['environment']
    max_time = int(config['max_time'])
    max_attempts = int(config['max_attempts'])
    sleep_time = int(config['sleep_time'])
    amqp_queue_name = config['amqp_queue_name']

# Try to decode message
    try:
#        nagios_data =  json.loads(str(body))
        nagios_data =  json.loads(str(body))
        LOG.info('Nagios data: \n {} \n '.format(json.dumps(nagios_data,sort_keys=True, indent=4)))
    except Exception as E:
# If message cn't be decoded we need to remove ot from queue and record to log.
# May be need to create some spetial alert on it?
        LOG.info('Nagios data cant be decoded: \n {} \n '.format(body))
        LOG.info(E)
        ch.basic_ack(delivery_tag = method.delivery_tag)
        return None


    payload = {
        'long_date_time':    nagios_data['long_date_time']
    }


# If affected_host is defined, use it for hostname,
# otherwise use host_name, which is usually 'glogal'

    Alert_ID  = environment
    Subject = ''

    if nagios_data['service_description']  != '':
        Alert_ID = '{}--{}'.format(Alert_ID, nagios_data['service_description'])
        Subject =  nagios_data['service_description']
        payload['service'] = nagios_data['service_description']


    if nagios_data['affected_hosts'] != []:
        Subject  =  '{}  {}'.format(Subject,nagios_data['affected_hosts'][0])
    else:
        Subject  =  '{}  {}'.format(Subject,nagios_data['host_name'])

    Alert_ID =  '{}--{}'.format(Alert_ID,nagios_data['host_name'])

    if nagios_data['long_service_output'] != '':
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




        #  If Case exist
        if (new_case.status_code  == 400) and (new_case.json()[0]['errorCode'] == 'DUPLICATE_VALUE'):
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
            # Ack
            ch.basic_ack(delivery_tag = method.delivery_tag)
            return
        # Else If Case did not exist before and was just  created
        elif  (new_case.status_code  == 201):
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
            # Ack
            ch.basic_ack(delivery_tag = method.delivery_tag)
            return
        else:
            LOG.info('Unexpected error: Case was not created (code !=201) and Case does not exist (code != 400), raising exeption!')
            raise requests.exceptions.ConnectionError

    except requests.exceptions.ConnectionError as E:
        LOG.info(E)

        LOG.info('Unexpected error: Case was not created (code !=201) and Case does not exist (code != 400) or connection error')
        new_body = json.loads(str(body))
        LOG.info('Failed to sent, updating message:  \n {}  \n '.format(json.dumps(new_body,sort_keys=True, indent=4)))

        # delete message if max_attempts were done
        if ( int(new_body['sfdc_attempts']) >  max_attempts ):
            LOG.info('Removing  message: sfdc_attempts = {}, max_attempts = {} '.format(new_body['sfdc_attempts'], max_attempts))
            ch.basic_ack(delivery_tag = method.delivery_tag)
            return
        else:
            new_body['sfdc_attempts'] = str(int(new_body['sfdc_attempts']) + 1)


        now_time = int(time.time())
        if ( now_time - int(new_body['publishing_time']) > max_time ):
            LOG.info('Removing  message: publishing_time = {}, now_time = {}, max_time = {} '.format(new_body['publishing_time'], now_time, max_time))
            ch.basic_ack(delivery_tag = method.delivery_tag)
            return
        # if message is not too old and we have not done enouth attempts to send it, remove old and create new with attemts = attempts +1 
        # remove
        ch.basic_ack(delivery_tag = method.delivery_tag)
        # publish new modified message


        channel.basic_publish(exchange='',
                      routing_key = amqp_queue_name,
                      body = json.dumps(new_body),
                      properties = properties)


        # no  sense to try again right after fail so sleep some time
        now_time = int(time.time())
        LOG.info('Starting sleep: sleep_time = {}, now = {} '.format(sleep_time, now_time))
        time.sleep(sleep_time)
        now_time = int(time.time())
        LOG.info('Sleep Finished: sleep_time = {}, now = {} '.format(sleep_time, now_time))







def main():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.yml')

    args = parser.parse_args()


# parse config file
    with open(args.config_file) as fp:
        config = yaml.safe_load(fp)

        amqp_hosts       = config['amqp_hosts'].split(',')


        amqp_user       = config['amqp_user']
        amqp_password   = config['amqp_password']
        amqp_queue_name = config['amqp_queue_name']

        host_regexp = config['host_regexp']
        log_file    = config['log_file']
        sleep_time = int(config['sleep_time'])

        environment          = config['environment']
        sfdc_client_id       = config['sfdc_client_id']
        sfdc_client_secret   = config['sfdc_client_secret']
        sfdc_username        = config['sfdc_username']
        sfdc_password        = config['sfdc_password']
        sfdc_auth_url        = config['sfdc_auth_url']
        sfdc_organization_id = config['sfdc_organization_id']





    LOG = logging.getLogger()

    handler = logging.FileHandler(log_file)

    log_level = logging.DEBUG

    formatter = logging.Formatter(
        '{} nagios_to_sfdc %(asctime)s %(process)d %(levelname)s %(name)s '
        '[-] %(message)s'.format(socket.getfqdn()),
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler.setFormatter(formatter)
    LOG.setLevel(log_level)
    LOG.addHandler(handler)


    print ' [*] Waiting for messages. To exit press CTRL+C'

    sfdc_oauth2 = OAuth2(client_id=sfdc_client_id,
                             client_secret=sfdc_client_secret,
                             username=sfdc_username,
                             password=sfdc_password,
                             auth_url=sfdc_auth_url,
                             organizationId = sfdc_organization_id )

    sfdc_client = Client(sfdc_oauth2)


    current_attempt  = 0
    for amqp_conn_string in itertools.cycle(amqp_hosts):
        amqp_host = amqp_conn_string.split(':')[0]
        amqp_port = int(amqp_conn_string.split(':')[1])

        try:
            LOG.info('Connecting to RabbitMQ,  amqp_conn_string = {},  amqp_host = {}, amqp_port = {}, current_attempt = {} '.format(amqp_conn_string, amqp_host, amqp_port, current_attempt))
            credentials = pika.PlainCredentials(amqp_user, amqp_password)

            pareameters = pika.ConnectionParameters(amqp_host, amqp_port, '/', credentials)
            connection = pika.BlockingConnection(pareameters)
            properties=pika.BasicProperties(delivery_mode = 2,)

            channel = connection.channel()
            channel.queue_declare(queue=amqp_queue_name, durable=True)

            callback = partial(callback2, config=config, LOG=LOG, sfdc_client = sfdc_client, channel = channel )

            channel.basic_consume(callback,queue=amqp_queue_name)
            channel.start_consuming()
        except Exception as E:
            LOG.info('Fauled to connect to RabbitMQ,  amqp_conn_string = {},  amqp_host = {}, amqp_port = {}, current_attempt = {} '.format(amqp_conn_string, amqp_host, amqp_port, current_attempt))
            LOG.info(E)
            LOG.info('Starting sleep: sleep_time = {}, now = {} '.format(sleep_time, int(time.time())))
            time.sleep(sleep_time)
            LOG.info('Sleep Finished: sleep_time = {}, now = {} '.format(sleep_time, int(time.time())))
            current_attempt = current_attempt +1

    print ' [*] Shutting down'





if __name__ == '__main__':
    main()
