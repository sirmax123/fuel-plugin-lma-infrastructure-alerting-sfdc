import json
import logging
import requests
import urllib3
import xml.dom.minidom

urllib3.disable_warnings()
LOG = logging.getLogger()


def send_to_sfdc(nagios_data, sfdc_client, environment):

    LOG.info('Starting sendig to SFDC... ')

    payload = {
        'long_date_time':    nagios_data['long_date_time']
    }

# If affected_host is defined, use it for hostname,
# otherwise use host_name, which is usually 'global-...'
    Alert_ID = environment
    Subject = ''

    if nagios_data['service_description']:
        Alert_ID = '{}--{}'.format(Alert_ID, nagios_data['service_description'])
        Subject = nagios_data['service_description']
        payload['service'] = nagios_data['service_description']

    if nagios_data['affected_hosts']:
        Subject = '{}  {}'.format(Subject, ' '.join(nagios_data['affected_hosts']))
        payload['affected_hosts'] = nagios_data['affected_hosts']
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

    LOG.info('Alert Data:\n{}\n'.format(json.dumps(alert_data, sort_keys=True, indent=4)))

    try:
        new_case = sfdc_client.create_case(alert_data)

        LOG.info('New Caset status code: {} '.format(new_case.status_code))
        LOG.info('New Case data: {} '.format(new_case.text))

        #  If Case exist
        if (new_case.status_code == 400) and (new_case.json()[0]['errorCode'] == 'DUPLICATE_VALUE'):
            LOG.info('Code: {}, Error message: {} '.format(new_case.status_code, new_case.text))
            # Find Case ID
            ExistingCaseId = new_case.json()[0]['message'].split(' ')[-1]

            current_case = sfdc_client.get_case(ExistingCaseId).json()
            LOG.info("Existing Case: \n {}".format(json.dumps(current_case, sort_keys=True, indent=4)))
            ExistingCaseStatus = current_case['Status']
            feed_data_body['Status'] = ExistingCaseStatus
            alert_data['Subject'] = current_case['Subject']

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
            return True
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
            return True
        else:
            LOG.info('Unexpected error: Case was not created (code != 201) and Case does not exist (code != 400)')
            return False

    except requests.exceptions.ConnectionError as e:
        LOG.info(e)
        LOG.info('Unexpected error: Case was not created: Connection error.')
        return False


class OAuth2(object):
    def __init__(self, client_id, client_secret, username, password, auth_url=None, organizationId=None):
        if not auth_url:
            auth_url = 'https://login.salesforce.com'

        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.organizationId = organizationId

    def getUniqueElementValueFromXmlString(self, xmlString, elementName):
        """
        Extracts an element value from an XML string.

        For example, invoking
        getUniqueElementValueFromXmlString('<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
        should return the value 'bar'.
        """
        xmlStringAsDom = xml.dom.minidom.parseString(xmlString)
        elementsByName = xmlStringAsDom.getElementsByTagName(elementName)
        elementValue = None
        if len(elementsByName) > 0:
            elementValue = elementsByName[0].toxml().replace('<' + elementName + '>', '').replace('</' + elementName + '>', '')
        return elementValue

    def authenticate_soap(self):

        soap_url = '{}/services/Soap/u/36.0'.format(self.auth_url)

        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
        <soapenv:Envelope
                xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:urn="urn:partner.soap.sforce.com">
            <soapenv:Header>
                <urn:CallOptions>
                    <urn:client>RestForce</urn:client>
                    <urn:defaultNamespace>sf</urn:defaultNamespace>
                </urn:CallOptions>
                <urn:LoginScopeHeader>
                    <urn:organizationId>{organizationId}</urn:organizationId>
                </urn:LoginScopeHeader>
            </soapenv:Header>
            <soapenv:Body>
                <urn:login>
                    <urn:username>{username}</urn:username>
                    <urn:password>{password}</urn:password>
                </urn:login>
            </soapenv:Body>
        </soapenv:Envelope>""".format(username=self.username, password=self.password, organizationId=self.organizationId)

        login_soap_request_headers = {
            'content-type': 'text/xml',
            'charset': 'UTF-8',
            'SOAPAction': 'login'
        }

        response = requests.post(soap_url, login_soap_request_body, verify=None, headers=login_soap_request_headers)

        LOG.debug(response)
        LOG.debug(response.status_code)
        LOG.debug(response.text)

        session_id = self.getUniqueElementValueFromXmlString(response.content, 'sessionId')
        server_url = self.getUniqueElementValueFromXmlString(response.content, 'serverUrl')

        response_json = {
            'access_token': session_id,
            'instance_url': self.auth_url
        }

        session_id = self.getUniqueElementValueFromXmlString(response.content, 'sessionId')
        response.raise_for_status()
        return response_json

    def authenticate_rest(self):
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.username,
            'password': self.password,
        }

        url = '{}/services/oauth2/token'.format(self.auth_url)
        response = requests.post(url, verify=None, data=data)
        response.raise_for_status()
        return response.json()

    def authenticate(self, **kwargs):
        if self.organizationId:
            LOG.debug('self.organizationId={}'.format(self.organizationId))
            LOG.debug('Auth method = SOAP')
            return self.authenticate_soap(**kwargs)
        else:
            LOG.debug('Auth method = REST')
            return self.authenticate_rest(**kwargs)


class Client(object):
    def __init__(self, oauth2):
        self.oauth2 = oauth2

        self.access_token = None
        self.instance_url = None

    def ticket(self, id):
        try:
            return self.get('/services/data/v36.0/sobjects/proxyTicket__c/{}'.format(id)).json()
        except requests.HTTPError:
            return False

    def create_mos_alert(self, data):
        return self.post('/services/data/v36.0/sobjects/MOS_Alerts__c', data=json.dumps(data), headers={"content-type": "application/json"})

    def create_mos_alert_comment(self, data):
        return self.post('/services/data/v36.0/sobjects/MOS_Alert_Comment__c', data=json.dumps(data), headers={"content-type": "application/json"})

    def get_mos_alert_comment(self, id):
        return self.get('/services/data/v36.0/sobjects/MOS_Alert_Comment__c/{}'.format(id))

    def del_mos_alert_comment(self, id):
        return self.delete('/services/data/v36.0/sobjects/MOS_Alert_Comment__c/{}'.format(id))

    def create_feeditem(self, data):
        return self.post('/services/data/v36.0/sobjects/FeedItem', data=json.dumps(data), headers={"content-type": "application/json"})

    def create_case(self, data):
        return self.post('/services/data/v36.0/sobjects/Case', data=json.dumps(data), headers={"content-type": "application/json"})

    def create_ticket(self, data):
        return self.post('/services/data/v36.0/sobjects/Case', data=json.dumps(data), headers={"content-type": "application/json"}).json()

    def get_case(self, id):
        return self.get('/services/data/v36.0/sobjects/Case/{}'.format(id))

    def get_mos_alert(self, id):
        return self.get('/services/data/v36.0/sobjects/MOS_Alerts__c/{}'.format(id))

    def del_mos_alert(self, id):
        return self.delete('/services/data/v36.0/sobjects/MOS_Alerts__c/{}'.format(id))

    def update_ticket(self, id, data):
        return self.patch('/services/data/v36.0/sobjects/proxyTicket__c/{}'.format(id), data=json.dumps(data), headers={"content-type": "application/json"})

    def update_mos_alert(self, id, data):
        return self.patch('/services/data/v36.0/sobjects/MOS_Alerts__c/{}'.format(id), data=json.dumps(data), headers={"content-type": "application/json"})

    def update_case(self, id, data):
        return self.patch('/services/data/v36.0/sobjects/Case/{}'.format(id), data=json.dumps(data), headers={"content-type": "application/json"})

    def update_comment(self, id, data):
        return self.patch('/services/data/v36.0/sobjects/proxyTicketComment__c/{}'.format(id), data=json.dumps(data), headers={"content-type": "application/json"})

    def create_ticket_comment(self, data):
        return self.post('/services/data/v36.0/sobjects/proxyTicketComment__c', data=json.dumps(data), headers={"content-type": "application/json"}).json()

    def environment(self, id):
        return self.get('/services/data/v36.0/sobjects/Environment__c/{}'.format(id)).json()

    def ticket_comments(self, ticket_id):
        return self.search("SELECT Comment__c, CreatedById, external_id__c, Id, CreatedDate, createdby.name "
                           "FROM proxyTicketComment__c "
                           "WHERE related_id__c='{}'".format(ticket_id))

    def ticket_comment(self, comment_id):
        return self.get('/services/data/v36.0/query',
                        params=dict(q="SELECT Comment__c, CreatedById, Id "
                                      "FROM proxyTicketComment__c "
                                      "WHERE external_id__c='{}'".format(comment_id))).json()

    def search(self, query):
        response = self.get('/services/data/v36.0/query', params=dict(q=query)).json()
        while True:
            for record in response['records']:
                yield record

            if response['done']:
                return

            response = self.get(response['nextRecordsUrl']).json()

    def get(self, url, **kwargs):
        return self._request('get', url, **kwargs)

    def patch(self, url, **kwargs):
        return self._request('patch', url, **kwargs)

    def post(self, url, **kwargs):
        return self._request('post', url, **kwargs)

    def delete(self, url, **kwargs):
        return self._request('delete', url, **kwargs)

    def delete1(self, url, **kwargs):
        return self._request('post', url, **kwargs)

    def _request(self, method, url, headers=None, **kwargs):
        if not headers:
            headers = {}

        if not self.access_token or not self.instance_url:
            result = self.oauth2.authenticate()
            self.access_token = result['access_token']
            self.instance_url = result['instance_url']

        headers['Authorization'] = 'Bearer {}'.format(self.access_token)

        url = self.instance_url + url

        response = requests.request(method, url, headers=headers, verify=None, **kwargs)


# Debug only
        LOG.debug("salesforce.py: Response code: {}".format(response.status_code))
        try:
            LOG.debug("salesforce.py: Response content: {}".format(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': '))))

            if (response.json()[0]['errorCode'] == 'INVALID_SESSION_ID'):
                LOG.debug("salesforce.py: Trying  gain")
                result = self.oauth2.authenticate()
                self.access_token = result['access_token']
                self.instance_url = result['instance_url']
                headers['Authorization'] = 'Bearer {}'.format(self.access_token)
                response = requests.request(method, url, headers=headers, verify=None, **kwargs)
        except Exception:
            LOG.debug("salesforce.py: Response content: {}".format(response.content))

        return response
