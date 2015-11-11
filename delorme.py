#!/usr/bin/env python2.7
import click
import requests
import itertools

from tabulate import tabulate

class Delorme(object):

    delorme_url = 'https://explore.delorme.com'
    delorme_cookie = '.ASPXAUTH'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None

    def _request(self, uri, method='GET', **kwargs):
        # get url
        url = '%s/%s' % (self.delorme_url, uri)

        # get cookies
        cookies = dict()
        if self.token:
            cookies[self.delorme_cookie] = self.token

        # execute request
        fn = getattr(requests, method.lower())
        r = fn(url, cookies=cookies, **kwargs)
        r.raise_for_status()
        return r

    def login(self, uri='/Account/LogOn'):
        r = self._request(uri, method='POST',
                               data={'UserName': self.username,
                                     'Password': self.password,
                                     'RememberMe': False},
                               allow_redirects=False)
        self.token = r.cookies[self.delorme_cookie]

    def upload(self, path):
        if self.token is None:
            self.login()

    def routes(self, uri='/Routes'):
        if self.token is None:
            self.login()

        r = self._request(uri)
        return r.json()


@click.group()
@click.option('--username', '-u', default=None, prompt=True)
@click.option('--password', '-p', default=None, prompt=True, hide_input=True)
@click.pass_context
def cli(ctx, username, password):
    ctx.obj = Delorme(username, password)


@cli.group(invoke_without_command=True)
@click.pass_obj
@click.pass_context
def routes(ctx, delorme):
    if ctx.invoked_subcommand is None:
        headers = ['Label', 'RouteID', 'CreatedDate', 'ModifiedDate']
        routes = [{k: v for k,v in r.items() if k in headers} for r in delorme.routes()]
        print tabulate(routes, headers='keys', tablefmt="plain") 


@routes.command('show')
@click.argument('file', nargs=-1, type=click.Path(exists=True))
@click.pass_obj
@click.pass_context
def routes_show(ctx, delorme):
    print delorme.routes()[-1]


@routes.command('upload')
@click.pass_obj
@click.pass_context
def routes_upload(ctx, delrome):
    pass

if __name__ == '__main__':
    cli()
