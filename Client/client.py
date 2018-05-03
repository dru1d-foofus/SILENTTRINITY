#! /usr/bin/env python2.7

from __future__ import unicode_literals, print_function
from core.helpers import KThread
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from terminaltables import AsciiTable
from socketIO_client import SocketIO, BaseNamespace
from requests.exceptions import ConnectionError
from time import sleep
import argparse
import inspect
import requests
import sys
import logging

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.getLogger("urllib3").setLevel(logging.WARNING)
# logging.getLogger('requests').setLevel(logging.WARNING)

logging.basicConfig(format="[%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


class InvalidCommand(Exception):
    pass


class UserExit(Exception):
    pass


class AuthenticationError(Exception):
    pass


def authenticate():
    try:
        r = requests.post(
            '{}://{}:{}/api/auth'.format('https' if not args.no_encryption else 'http', args.ip, args.port),
            json={'username': args.username, 'password': args.server_password},
            verify=False
        )

        return {'Authorization': 'JWT ' + r.json()['access_token']}
    except KeyError:
        raise AuthenticationError('Unable to retrieve access token, invalid username or password')
    except ConnectionError as e:
        raise ConnectionError('Failed to connect to server: {}'.format(e))


history = InMemoryHistory()


class STShell(object):

    def __init__(self):
        self.selected = None
        self.prompt = ''

    def help(self, args):
        if not args:
            table_data = [
                ['Command', 'Description']
            ]

            for command in self._get_commands():
                table_data.append([command, getattr(self, command).__doc__])

            table = AsciiTable(table_data)
            table.inner_row_border = True
            print(table.table)
        else:
            if args[0] in self._get_commands():
                command = args[0]
                print(getattr(self, command).__doc__)

    def back(self, args):
        '''Go back to the previous menu'''

        raise UserExit

    def exit(self, args):
        '''Exit the ST Client'''

        sys.exit(0)

    def login(self, args):
        '''Login to the specified server'''

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

    def _bottom_toolbar(self):
        # socket.emit('') Poll the server for the current user's data
        return [('class:bottom-toolbar', 'Connected - {}@{}:{} sessions: {}'.format(args.username, args.ip, args.port, 0))]

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
                    bottom_toolbar=self._bottom_toolbar,
                    refresh_interval=1
                )

                if len(result):
                    cmd, args = result.split()[0], result.split()[1:]
                    logging.debug('cmd: {} args: {}'.format(repr(cmd), args))
                    if hasattr(self, cmd) and cmd not in local_commands:
                        socket.emit('{}.{}'.format(self.__class__.__name__.lower(), cmd), {'args': args, 'selected': self.selected})
                    elif cmd in local_commands and hasattr(self, cmd):
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
        raise UserExit

    def start(self, data):
        if data['result']:
            logging.info("Listener '{}' started successfully!".format(data['name']))
            return

        logging.error('Listener failed to start')

    def stop(self, data):
        if data['result']:
            logging.info("Listener '{}' stopped successfully!".format(data['name']))
            return

        logging.error('Listener failed to stop')


class Sessions(STShell):
    def __init__(self):
        self.selected = None
        self.prompt = 'ST (sessions) > '

    def available(self, data):
        pass

    def listeners(self, args):
        raise UserExit


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

    def on_connect(self, *args):
        logging.warning('Connected to server')

    def on_disconnect(self, *args):
        logging.warning('Disconnected from server')
        while True:
            try:
                auth_headers = authenticate()
                self._io._http_session.headers.update(auth_headers)
                break
            except Exception as e:
                logging.warning(str(e))
                sleep(1)

    def on_reconnect(self, *args):
        logging.warning('Reconnected to server')

    def on_error(self, data):
        logging.warning('Got error: {}'.format(data))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('ip', nargs=1, type=str, help='Teamserver IP')
    parser.add_argument('username', nargs=1, type=str, help='Username')
    parser.add_argument('server_password', nargs=1, type=str, help='Teamserver password')
    parser.add_argument('-p', '--port', default=5000, type=int, help='Teamserver port')
    parser.add_argument('--no-encryption', action='store_true', help='Disable TLS between the client and server')
    args = parser.parse_args()

    args.ip = args.ip[0]
    args.username = args.username[0]
    args.server_password = args.server_password[0]

    listeners = Listeners()
    sessions = Sessions()
    setattr(STNamespace, 'listeners', listeners)
    setattr(STNamespace, 'sessions', sessions)
    main_menu = MainMenu(listeners, sessions)

    socketio_args = {
        'host': '{}://{}'.format('https' if not args.no_encryption else 'http', args.ip),
        'port': args.port,
        'Namespace': STNamespace,
        'verify': False,
        'headers': authenticate()
    }

    if not args.no_encryption:
        socketio_args['cert'] = ('client.crt', 'client.key')

    socket = SocketIO(**socketio_args)

    t = KThread(target=socket.wait)
    t.setDaemon(True)
    t.start()

    main_menu()
