#! /usr/bin/env python2.7

from __future__ import unicode_literals, print_function
#from functools import wraps
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from terminaltables import AsciiTable
from socketIO_client import SocketIO, BaseNamespace
import requests
import sys
import logging
import threading

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


s = requests.Session()
server = '127.0.0.1:5000'

username = 'admin'
password = 'admin'


def bottom_toolbar():
    return [('class:bottom-toolbar', ' This is a toolbar.')]


history = InMemoryHistory()


class STShell(object):
    def __init__(self):
        self.registered_commands = {}

    def register(self, name=None):
        def func_wrapper(func):
            if name is None:
                name = func.__name__
            self.registered_commands[name] = func
            return func
        return func_wrapper

    def get_registered(self, name=None):
        func = self.func_map.get(name, None)
        if func is None:
            raise Exception("No function registered against - " + str(name))
        return func

    def __call__(self):
        while True:
            try:
                result = prompt('ST > ', history=history, auto_suggest=AutoSuggestFromHistory(), bottom_toolbar=bottom_toolbar, refresh_interval=.5)
                cmd, args = result.split()[0], result.split()[1:]
                self.get_registered(cmd)(args)
            except KeyboardInterrupt:
                break


class STListeners(STShell):
    pass


class STSessions(STShell):
    pass


class STMainMenu(STShell):
    def __init__(self):
        self.listeners = STListeners()
        self.sessions = STSessions()

    @register
    def listeners(self, args):
        self.listeners()

    @register
    def sessions(self, args):
        self.sessions()

    @register
    def login(self, args):
        print('yay')

    @register
    def help(self, args):
        pass

    @register
    def back(self, args):
        raise KeyboardInterrupt

    @register
    def exit(self, args):
        raise KeyboardInterrupt


class STNamespace(BaseNamespace):

    def on_connect(self):
        logging.info('Connected')

    def on_reconnect(self):
        logging.info('Reconnected')

    def on_disconnect(self):
        logging.info('Disconnected')

    def on_response(self, *args):
        logging.info('on_response: {}'.format(args))

    def on_new_session(self, *args):
        logging.info('on_new_session: {}'.format(args))


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

    menu = STMainMenu()
    menu()
