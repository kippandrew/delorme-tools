#!/usr/bin/env python2.7
import os
import sys
import logging

import click
import requests

from tabulate import tabulate

logger = logging.getLogger('delorme')

class Delorme(object):

    delorme_url = 'https://explore.delorme.com'
    delorme_cookie = '.ASPXAUTH'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None

    def _request(self, uri, method='GET', **kwargs):
        # get url
        url = '%s%s' % (self.delorme_url, uri)

        # get cookies
        cookies = dict()
        if self.token:
            cookies[self.delorme_cookie] = self.token

        # execute request
        fn = getattr(requests, method.lower())
        r = fn(url, cookies=cookies, **kwargs)

        logger.debug('%s %s (%s)', method.upper(), url, r.status_code)

        r.raise_for_status()
        return r

    def login(self, uri='/Account/LogOn'):
        r = self._request(uri, method='POST',
                               data={'UserName': self.username,
                                     'Password': self.password,
                                     'RememberMe': False},
                               allow_redirects=False)
        self.token = r.cookies[self.delorme_cookie]

    def routes(self):
        if self.token is None:
            self.login()
        return self._request('/Routes').json()

    def save_route(self, route_data):
        if self.token is None:
            self.login()
        return self._request('/Routes/Save', method='POST').json()

    def delete_route(self, route_id):
        if self.token is None:
            self.login()
        r = self._request('/Routes/Delete/%d' % (route_id), method='POST')
        return not r.text

    def waypoints(self):
        if self.token is None:
            self.login()
        return self._request('/Waypoints').json()

    def save_waypoint(self, waypoint_data):
        if self.token is None:
            self.login()
        return self._request('/Waypoints/Save', method='POST').text

    def delete_waypoint(self, route_id):
        if self.token is None:
            self.login()
        r = self._request('/Waypoints/Delete/%d' % (route_id), method='DELETE')
        return not r.text

    def import_data(self, path):
        if self.token is None:
            self.login()
        r = self._request('/User/Data/Import',
                          method='POST',
                          files = {'file': (os.path.basename(path), open(path, 'rb'), 'application/octet-stream')})
        result = r.json()
        return result.get('ImportResults')

    def export_data(self, path):
        pass


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
    routes = [[r[k] for k in headers] for r in delorme.routes()]
    print tabulate(routes, headers, tablefmt="simple")


@route.command('show')
@click.argument('route_id', type=click.INT)
@click.pass_obj
def routes_show(delorme):
    print delorme.routes()[-1]


@route.command('delete')
@click.argument('route_id', type=click.INT)
@click.pass_obj
def routes_delete(delorme, route_id):
    if delorme.delete_route(route_id):
        print 'Deleted route: %d' % route_id


@cli.command('import')
@click.argument('file', type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def import_data(ctx, delorme, file):
    result = delorme.import_data(file)
    headers = ['RouteId', 'Label']
    imported = [[r[k] for k in headers] for r in result['RouteImports']]
    print tabulate(imported, headers, tablefmt='simple')


if __name__ == '__main__':
    cli()
