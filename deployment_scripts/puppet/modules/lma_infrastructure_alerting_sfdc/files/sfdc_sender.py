#!/usr/bin/env python

from argparse import ArgumentParser
from functools import partial
from datetime import datetime
import dateutil.parser
import itertools
import json
import logging
import os
import pika
import requests
from salesforce import OAuth2, Client, send_to_sfdc
import socket
import sys
import time
import yaml


def callback2(ch, method, properties, body, config, LOG, sfdc_client, channel=None):

    LOG.info('Starting ... ')
    environment = config['environment']
    max_time = int(config['max_time'])
    max_attempts = int(config['max_attempts'])
    sleep_time = int(config['sleep_time'])
    amqp_queue_name = config['amqp_queue_name']
# Try to decode message
    try:
        nagios_data = json.loads(str(body))
        LOG.info('Nagios data: \n {} \n '.format(json.dumps(nagios_data, sort_keys=True, indent=4)))
    except Exception as E:
        # If message can't be decoded we need to remove it from queue and record to log.
        # May be need to create some spetial alert on it?
        LOG.info('Nagios data cant be decoded: \n {} \n '.format(body))
        LOG.info(E)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return None

    if send_to_sfdc(nagios_data=nagios_data, sfdc_client=sfdc_client, environment=environment):
        # Sent to SFDC w/o errors, remove from queue
        LOG.info('Message was sent, nagios data":  \n{}  \n '.format(json.dumps(nagios_data, sort_keys=True, indent=4)))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        # was not sent
        LOG.info('Failed to sent, updating message:  \n{}  \n '.format(json.dumps(nagios_data, sort_keys=True, indent=4)))
        # Delete message if max_attempts attempts were done
        if (int(nagios_data['sfdc_attempts']) > max_attempts):
            LOG.info('Removing  message: sfdc_attempts = {}, max_attempts = {} '.format(nagios_data['sfdc_attempts'], max_attempts))
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        elif (int(time.time()) - int(nagios_data['publishing_time']) > max_time):
            LOG.info('Removing  message: publishing_time = {}, now_time = {}, max_time = {} '.format(nagios_data['publishing_time'], int(time.time()), max_time))
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        else:
            nagios_data['sfdc_attempts'] = str(int(nagios_data['sfdc_attempts']) + 1)

            # If message is not too old and we have not done enouth attempts to send it,
            # remove old and create new with attemts = attempts + 1
            ch.basic_ack(delivery_tag=method.delivery_tag)

            # Publish new modified message
            channel.basic_publish(exchange='',
                                  routing_key=amqp_queue_name,
                                  body=json.dumps(nagios_data),
                                  properties=properties)

            # No sense to try again right after fail so sleep some time
            now_time = int(time.time())
            LOG.info('Starting sleep: sleep_time = {}, now = {} '.format(sleep_time, now_time))
            time.sleep(sleep_time)
            now_time = int(time.time())
            LOG.info('Sleep Finished: sleep_time = {}, now = {} '.format(sleep_time, now_time))


def main():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.yml')

    args = parser.parse_args()


# Parse config file
    with open(args.config_file) as fp:
        config = yaml.safe_load(fp)
        amqp_hosts = config['amqp_hosts'].split(',')
        amqp_user = config['amqp_user']
        amqp_password = config['amqp_password']
        amqp_queue_name = config['amqp_queue_name']
        host_regexp = config['host_regexp']
        log_file = config['log_file']
        sleep_time = int(config['sleep_time'])
        environment = config['environment']
        sfdc_client_id = config['sfdc_client_id']
        sfdc_client_secret = config['sfdc_client_secret']
        sfdc_username = config['sfdc_username']
        sfdc_password = config['sfdc_password']
        sfdc_auth_url = config['sfdc_auth_url']
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

    logging.getLogger("pika").setLevel(logging.CRITICAL)
    LOG.info(' [*] Waiting for messages. To exit press CTRL+C')
    print ' [*] Waiting for messages. To exit press CTRL+C'

    sfdc_oauth2 = OAuth2(client_id=sfdc_client_id,
                         client_secret=sfdc_client_secret,
                         username=sfdc_username,
                         password=sfdc_password,
                         auth_url=sfdc_auth_url,
                         organizationId=sfdc_organization_id)

    sfdc_client = Client(sfdc_oauth2)

    current_attempt = 0
    for amqp_conn_string in itertools.cycle(amqp_hosts):
        amqp_host = amqp_conn_string.split(':')[0].strip()
        amqp_port = int(amqp_conn_string.split(':')[1].strip())

        try:
            LOG.info('Connecting to RabbitMQ,  amqp_conn_string = {},  amqp_host = {}, amqp_port = {}, current_attempt = {} '.format(amqp_conn_string, amqp_host, amqp_port, current_attempt))
            credentials = pika.PlainCredentials(amqp_user, amqp_password)

            pareameters = pika.ConnectionParameters(amqp_host, amqp_port, '/', credentials)
            connection = pika.BlockingConnection(pareameters)
            properties = pika.BasicProperties(delivery_mode=2,)

            channel = connection.channel()
            channel.queue_declare(queue=amqp_queue_name, durable=True)

            callback = partial(callback2, config=config, LOG=LOG, sfdc_client=sfdc_client, channel=channel)

            channel.basic_consume(callback, queue=amqp_queue_name)
            channel.start_consuming()
        except Exception as E:
            LOG.info('Failed to connect to RabbitMQ,  amqp_conn_string = {},  amqp_host = {}, amqp_port = {}, current_attempt = {} '.format(amqp_conn_string, amqp_host, amqp_port, current_attempt))
            LOG.info(E)
            LOG.info('Starting sleep: sleep_time = {}, now = {} '.format(sleep_time, int(time.time())))
            time.sleep(sleep_time)
            LOG.info('Sleep Finished: sleep_time = {}, now = {} '.format(sleep_time, int(time.time())))
            current_attempt = current_attempt + 1

    print ' [*] Shutting down'


if __name__ == '__main__':
    main()
