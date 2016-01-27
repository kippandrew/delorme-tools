#!/usr/bin/env python2.7
import json
import os
import sys
import logging
import re
import urllib

import click
import collections
import requests
import iso8601

from tabulate import tabulate

logger = logging.getLogger('delorme')


def uncamel(s):
    """
    Convert a CamelCase string to separate words
    :param s:
    :return:
    >>> uncamel("TestTestTest")
    'Test Test Test'
    """
    return re.sub(r'(?!^)([A-Z]+)', r' \1', s)


def from_timestamp(s):
    """
    Parse a timestamp to a datetime object
    :param s: string to convert to a datetime
    :return:
    """
    return iso8601.parse_date(s)


def to_timestamp(d):
    """
    :param d: datetime to convert to a string
    :return:
    """
    return d.isoformat()


def from_json(s):
    return json.loads(s)


def to_json(obj):
    return json.dumps(obj)


def id_list(obj):
    if not isinstance(obj, (list, tuple)):
        obj = [obj]
    return ','.join(map(str, obj))


DELORME_URL = 'https://explore.delorme.com'
DELORME_COOKIE = '.ASPXAUTH'

SERVICE_MESSAGES = 3
SERVICE_TRACKS = 6
SERVICE_NAVIGATION = 7


class DelormeError(Exception):
    pass


class Delorme(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def _request(self, uri, method='GET', token=None, **kwargs):
        # get url
        url = '%s%s' % (DELORME_URL, uri)

        cookies = dict()
        if token is not None:
            if token:
                cookies[DELORME_COOKIE] = token
        else:
            cookies[DELORME_COOKIE] = self.token

        # execute request
        fn = getattr(requests, method.lower())
        r = fn(url, cookies=cookies, **kwargs)

        logger.debug('%s %s (%s)', method.upper(), r.request.url, r.status_code)

        r.raise_for_status()
        return r

    def _error(self, r):
        pass

    @property
    def token(self):
        if not hasattr(self, '_token'):
            self._token = self.login()
        return self._token

    def login(self, uri='/Account/LogOn'):
        r = self._request(uri, method='POST',
                          data={'UserName': self.username,
                                'Password': self.password,
                                'RememberMe': False},
                          token=False,
                          allow_redirects=False)
        token = r.cookies.get(DELORME_COOKIE)
        if token is None:
            raise DelormeError("Authentication failed. Invalid username or password.")
        return token

    def get_routes(self):
        data = self._request('/Routes').json()
        for r in data:
            r['CreatedDate'] = from_timestamp(r['CreatedDate'])
        return data

    def save_route(self, route_data):
        return self._request('/Routes/Save', method='POST').json()

    def delete_route(self, route_id):
        r = self._request('/Routes/Delete/%d' % (route_id), method='POST')
        return not r.text

    def get_waypoints(self):
        return self._request('/Waypoints').json()

    def save_waypoint(self, waypoint_data):
        return self._request('/Waypoints/Save', method='POST').text

    def delete_waypoint(self, route_id):
        r = self._request('/Waypoints/Delete/%d' % (route_id), method='DELETE')
        return not r.text

    def import_data(self, path):
        r = self._request('/User/Data/Import',
                          method='POST',
                          files={'file': (os.path.basename(path), open(path, 'rb'), 'application/octet-stream')})
        result = r.json()
        return result.get('ImportResults')

    def get_users(self, user_id):
        r = self._request('/Configuration/Organization/GetOrganizations')
        result = r.json()
        return result[0]['users']

    def export_data(self, device_id, user_ids=None, from_date=None, to_date=None, service_types=None, file_type='GPX',
                    ignore_route_ids=None, ignore_waypoint_ids=None):

        # get user ids
        if user_ids is None:
            user_ids = device_id

        # get service types
        if service_types is None:
            service_types = [SERVICE_TRACKS]

        # get filter
        if from_date:
            filter = [{'criteriaId': 12, 'value': None, 'values':[to_timestamp(from_date)]}]
        elif from_date and to_date:
            filter = [{'criteriaId': 11, 'value': None, 'values':[to_timestamp(from_date), to_timestamp(to_date)]}]
        else:
            filter = [{'criteriaId': 10, 'value': 1}]  # most recent track

        r = self._request('/Map/GetDeviceListForDownload',
                          params={'deviceHistories': device_id,
                                  'deviceMenuItem': 'Active',
                                  'visibleUserIds': id_list(user_ids),
                                  'waypointsNotVisibleSyncIds': id_list(ignore_waypoint_ids),
                                  'invisibleRoutesSyncIds': id_list(ignore_route_ids),
                                  'fromDate': to_timestamp(from_date) if from_date else '',
                                  'toDate': to_timestamp(to_date) if to_date else '',
                                  'filter': to_json(filter),
                                  'fileType': file_type,
                                  'serviceTypes': id_list(service_types)})

        if not r.ok:
            self._error(r)

        # print r.content

@click.group()
@click.option('--username', '-u', default=None, prompt=True)
@click.option('--password', '-p', default=None, prompt=True, hide_input=True)
@click.option('--verbose', is_flag=True)
@click.pass_context
def cli(ctx, username, password, verbose):
    ctx.obj = Delorme(username, password)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.NOTSET)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if verbose:
        logger.setLevel(logging.DEBUG)


@cli.group()
def route():
    pass


@route.command('list')
@click.pass_obj
def list_routes(delorme):
    headers = ['RouteID', 'Label', 'CreatedDate', 'ModifiedDate']
    routes = [[r[k] for k in headers] for r in delorme.get_routes()]
    print tabulate(routes, map(uncamel, headers), tablefmt="simple")


@route.command('show')
@click.argument('route_id', type=click.INT)
@click.pass_obj
def routes_show(delorme):
    print delorme.get_routes()[-1]


@route.command('delete')
@click.argument('route_id', type=click.INT)
@click.pass_obj
def routes_delete(delorme, route_id):
    if delorme.delete_route(route_id):
        print 'Deleted route: %d' % route_id


@cli.command('import')
@click.argument('file', nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def import_data(ctx, delorme, file):
    for f in file:
        result = delorme.import_data(f)
        headers = ['RouteId', 'Label']
        imported = [[r[k] for k in headers] for r in result['RouteImports']]
        print tabulate(imported, map(uncamel, headers), tablefmt='simple')


@cli.command('export')
@click.argument('device_id', type=click.INT)
@click.pass_obj
@click.pass_context
def export_data(ctx, delorme, device_id):
    result = delorme.export_data(device_id, 64591)


if __name__ == '__main__':
    cli()
