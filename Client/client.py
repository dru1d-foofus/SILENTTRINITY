#! /usr/bin/env python2.7

from __future__ import unicode_literals, print_function
#from functools import wraps
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter
from terminaltables import AsciiTable
from socketIO_client import SocketIO, BaseNamespace
import argparse
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


status = ' This is a toolbar.'


def bottom_toolbar():
    return [('class:bottom-toolbar', status)]


history = InMemoryHistory()


class STShell(object):

    def __init__(self):
        self.selected = None
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

    def _print_table(self, data):
        table_data = [
            [key.capitalize() for key in data[0].keys()]
        ]

        for entry in data:
            table_data.append(entry.values())

        table = AsciiTable(table_data)
        print(table.table)

    def _print_list_of_tables(self, data):
        table_data = [
            [entry.keys()[0].capitalize() for entry in data],
        ]

        table_data.append([entry.values()[0] for entry in data])

        table = AsciiTable(table_data)
        print(table.table)

    def __call__(self):
        commands = self._get_commands()
        local_commands = ['help', 'back', 'exit', 'login', 'listeners', 'sessions']
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
                    if hasattr(self, cmd) and cmd not in local_commands:
                        socket.emit('{}.{}'.format(self.__class__.__name__.lower(), cmd), {'args': args, 'selected': self.selected})
                    elif cmd in local_commands:
                        getattr(self, cmd)(args)
                    else:
                        logging.debug('Command {} is not registered'.format(cmd))
            except KeyboardInterrupt:
                pass
            except UserExit:
                break


class Listeners(STShell):
    def __init__(self):
        self.selected = None
        self.prompt = 'ST (listeners) > '

    def available(self, data):
        self._print_table(data)

    def running(self, data):
        self._print_table(data)

    def use(self, data):
        if data['result']:
            self.selected = data['name']
            return
        logging.error('Error selecting listener')

    def set(self, data):
        if data['result']:
            return
        logging.error('Error setting listener value')

    def options(self, data):
        self._print_list_of_tables(data)

    def sessions(self, data):
        pass

    def start(self, data):
        pass

    def stop(self, data):
        pass


class Sessions(STShell):
    def __init__(self):
        self.selected = None
        self.prompt = 'ST (sessions) > '

    def listeners(self, args):
        pass


class MainMenu(STShell):
    def __init__(self, listeners, sessions):
        self.prompt = 'ST > '
        self.listeners_menu = listeners
        self.sessions_menu = sessions

    def listeners(self, args):
        self.listeners_menu()

    def sessions(self, args):
        self.sessions_menu()


class STNamespace(BaseNamespace):

    def on_event(self, event, *args):
        logging.debug('Received event: {} args: {}'.format(repr(event), args))
        name, event_name, method = event.lower().split('.')

        if name == 'response' and hasattr(self, event_name):
            cl = getattr(self, event_name)
            if hasattr(cl, method):
                if len(args[0]['data']):
                    logging.debug('Calling {}.{}'.format(event_name, method))
                    getattr(cl, method)(args[0]['data'])
                else:
                    logging.debug('Ignoring response as no data was returned')

    def on_new_session(self, *args):
        logging.debug('on_new_session: {}'.format(args))
        logging.info(args[0]['data'])

    def on_new_login(self, *args):
        logging.debug('on_new_login: {}'.format(args))
        logging.info(args[0]['data'])


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('ip', nargs=1, type=str, help='Teamserver IP')
    parser.add_argument('username', nargs=1, type=str, help='Username')
    parser.add_argument('server_password', nargs=1, type=str, help='Teamserver password')
    parser.add_argument('-p', '--port', default=5000, type=int, help='Teamserver port')
    args = parser.parse_args()

    args.ip = args.ip[0]
    args.username = args.username[0]
    args.server_password = args.server_password[0]

    listeners = Listeners()
    sessions = Sessions()
    setattr(STNamespace, 'listeners', listeners)
    setattr(STNamespace, 'sessions', sessions)
    main_menu = MainMenu(listeners, sessions)

    try:
        r = requests.post('http://{}:{}/api/auth'.format(args.ip, args.port), json={'username': args.username, 'password': args.server_password})
        auth_header = {'Authorization': 'JWT ' + r.json()['access_token']}
    except KeyError:
        logging.error('Unable to retrieve access token, invalid username or password')
        sys.exit(1)

    socket = SocketIO(args.ip, args.port, STNamespace, headers=auth_header)
    t = threading.Thread(target=socket.wait)
    t.setDaemon(True)
    t.start()

    status = 'Server: (127.0.0.1:5000)'

    main_menu()
