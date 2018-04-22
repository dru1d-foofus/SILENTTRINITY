#! /usr/bin/env python2.7

from __future__ import unicode_literals, print_function
#from functools import wraps
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter
from terminaltables import AsciiTable
from socketIO_client import SocketIO, BaseNamespace
import inspect
import requests
import sys
import logging
import threading

logging.basicConfig(format="[%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


class InvalidCommand(Exception):
    pass


class UserExit(Exception):
    pass

s = requests.Session()
server = '127.0.0.1:5000'

username = 'admin'
password = 'admin'
status = ' This is a toolbar.'


def bottom_toolbar():
    return [('class:bottom-toolbar', status)]


history = InMemoryHistory()


class STShell(object):

    def __init__(self):
        self.prompt = ''

    def help(self, args):
        pass

    def back(self, args):
        raise UserExit

    def exit(self, args):
        sys.exit(0)

    def login(self, args):
        username = prompt('Username: ')
        password = prompt('Password: ', is_password=True)

        print(username, password)

    def _get_commands(self):
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        commands = [method[0].decode('utf-8') for method in methods if not method[0].startswith('_')]
        return commands

    def __call__(self):
        commands = self._get_commands()
        logging.debug('Found commands: {}'.format(commands))

        while True:
            try:
                result = prompt(
                    self.prompt,
                    history=history,
                    auto_suggest=AutoSuggestFromHistory(),
                    completer=WordCompleter(commands),
                    bottom_toolbar=bottom_toolbar,
                    refresh_interval=.5
                )

                if len(result):
                    cmd, args = result.split()[0], result.split()[1:]
                    logging.debug('cmd: {} args: {}'.format(repr(cmd), args))
                    if hasattr(self, cmd):
                        getattr(self, cmd)(args)
                    else:
                        logging.debug('Command {} is not registered'.format(cmd))
            except KeyboardInterrupt:
                pass
            except UserExit:
                break


class STListeners(STShell):
    def __init__(self):
        self.selected_listener = None
        self.prompt = 'ST (listeners) > '

    def available(self, args):
        def print_available(data):
            table_data = [
                ['Name', 'Description'],
            ]

            for entry in data:
                table_data.append([entry['Name'], entry['Description']])

            table = AsciiTable(table_data)
            print(table.table)

        socket.on('response', lambda resp: print_available(resp['data']['available']))
        socket.emit('listeners', {})

    def running(self, args):
        pass

    def options(self, args):
        pass

    def sessions(self, args):
        pass


class STSessions(STShell):
    def __init__(self):
        self.prompt = 'ST (sessions) > '

    def listeners(self, args):
        pass


class STMainMenu(STShell):
    def __init__(self):
        self.prompt = 'ST > '
        self.stlisteners = STListeners()
        self.stsessions = STSessions()

    def listeners(self, args):
        self.stlisteners()

    def sessions(self, args):
        self.stsessions()


class STNamespace(BaseNamespace):

    def on_connect(self):
        logging.info('Connected')

    def on_reconnect(self):
        logging.info('Reconnected')

    def on_disconnect(self):
        logging.info('Disconnected')

    def on_response(self, *args):
        logging.debug('on_response: {}'.format(args))

    def on_new_session(self, *args):
        logging.debug('on_new_session: {}'.format(args))
        logging.info(args['data'])


if __name__ == '__main__':

    r = s.post('http://{}/api/auth'.format(server), json={'username': username, 'password': password})
    auth_header = {'Authorization': 'JWT ' + r.json()['access_token']}
    s.headers.update(auth_header)

    socket = SocketIO('127.0.0.1', 5000, STNamespace, headers=auth_header)
    #socket.emit('sessions', {})
    #socket.emit('listeners', {})
    t = threading.Thread(target=socket.wait)
    t.setDaemon(True)
    t.start()

    status = 'Server: (127.0.0.1:5000)'

    menu = STMainMenu()
    menu()
