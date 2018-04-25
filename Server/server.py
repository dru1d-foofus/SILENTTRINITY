#! /usr/bin/env python2.7

from __future__ import unicode_literals, print_function
#import rpyc
#import sys
from flask import Flask, make_response, jsonify, abort, request
from flask_socketio import SocketIO, emit, disconnect, Namespace
from flask_jwt import JWT, _jwt_required, JWTError, current_identity, _default_jwt_payload_handler
#from flask.json import JSONEncoder
from werkzeug.security import safe_str_cmp
from uuid import uuid4
#import threading
from rpyc.core import Service
#import flask
from core.arguments import get_arguments
import logging
import json
import os
import imp
import traceback
import zlib
import string
import random
#import marshal
from IPython import embed
import sys


logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


def gen_secret_key():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(40))


class User(object):
    def __init__(self, id, username):
        self.id = id
        self.username = username
        self.sid = None

    def __str__(self):
        return "User(id='{}' username='{}')".format(self.id, self.username)


class ConnectedUsers(object):

    def __init__(self):
        self.user_id = 1
        self.connected_users = []

    def get_user_from_username(self, username):
        for user in self.connected_users:
            if user.username == str(username):
                return user

        return None

    def get_user_from_sid(self, sid):
        for user in self.connected_users:
            if user.sid == str(sid):
                return user

        return None

    def get_user_from_id(self, id):
        for user in self.connected_users:
            if user.id == int(id):
                return user

        return None

    def remove_user(self, sid):
        for user in [user for user in self.connected_users if user.sid == str(sid)]:
            logging.debug('Removing user {}'.format(user))
            self.connected_users.remove(user)

    def add_user(self, username):
        user = User(self.user_id, str(username))
        self.connected_users.append(user)
        self.user_id += 1
        return user


def authenticate(username, password):
    if not connected_users.get_user_from_username(username) and safe_str_cmp(args.server_password.encode('utf-8'), password.encode('utf-8')):
        logging.debug('Client authenticated successfully')
        return connected_users.add_user(username)

    logging.debug('Client failed authentication')


def identity(payload):
    user_id = payload['identity']
    user = connected_users.get_user_from_id(user_id)
    if user:
        user.sid = request.sid

    return user

"""
class MyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, STObject):
            return obj.toJson()

        return super(MyJSONEncoder, self).default(obj)
"""

app = Flask(__name__)
app.config['SECRET_KEY'] = gen_secret_key()
app.config['JWT_AUTH_URL_RULE'] = '/api/auth'
#app.json_encoder = MyJSONEncoder
jwt = JWT(app, authenticate, identity)
socketio = SocketIO(app)  # , json=flask.json


class STService(Service):

    def on_connect(self):
        try:
            self._conn._config.update({
                "allow_safe_attrs": True,
                "allow_public_attrs": False,
                "allow_pickle": False,
                "allow_getattr": True,
                "allow_setattr": False,
                "allow_delattr": False,
                "import_custom_exceptions": False,
                "instantiate_custom_exceptions": False,
                "instantiate_oldstyle_exceptions": False,
            })

            #self._conn._config["safe_attrs"].add("__iter__")
            #self._conn._config["safe_attrs"].add("readline")

            self.modules = None

            try:
                self.namespace = self._conn.root.namespace
            except Exception:
                logging.error('Error setting namespace alias:')
                logging.error(traceback.format_exc())

            self.execute = self._conn.root.execute
            self.register_remote_cleanup = self._conn.root.register_cleanup
            self.unregister_remote_cleanup = self._conn.root.unregister_cleanup
            self.exit = self._conn.root.exit
            self.eval = self._conn.root.eval
            self.get_infos = self._conn.root.get_infos
            self.builtin = self.modules.__builtin__
            self.builtins = self.modules.__builtin__
            self.exposed_stdin = sys.stdin
            self.exposed_stdout = sys.stdout
            self.exposed_stderr = sys.stderr
            self.sessions._add_client(self)

        except Exception as e:
            logging.error("Caught error when receiving connection: {}".format(e))
            logging.error(traceback.format_exc())

    def on_disconnect(self):
        self.stsessions.remove_client(self)
        logging.info("Client disconnected")

    def exposed_set_modules(self, modules):
        self.modules = modules

    def exposed_json_dumps(self, js, compressed=False):
        data = json.dumps(js)
        if compressed:
            data = zlib.compress(data)

        return data


class STObject(object):
    pass


class STSessions(STObject):
    def __init__(self):
        self.sessions = {}

    def _add_client(self, conn):

        """
        with open('./utils/client_initializer.py') as initializer:
            conn.execute(
                'import marshal;exec marshal.loads({})'.format(
                    repr(marshal.dumps(compile(initializer.read(), '<loader>', 'exec')))
                )
            )
        """

        uid = str(uuid4())[:8]

        client_infos = conn.get_infos()

        logging.debug('Session returned client infos: {}'.format(client_infos))

        conn._conn._config['connid'] = uid

        listener_addr, listener_port = conn._conn._config['endpoints'][0]

        client_ip, client_port = conn._conn._config['endpoints'][1]

        status_line = "Session {} opened ({}@{}) ({}:{} <- {}:{})".format(
            uid,
            client_infos.get('user', '?'),
            client_infos.get('hostname', '?'),
            listener_addr,
            listener_port,
            client_ip,
            client_port)

        logging.info(status_line)

        emit('new_session', {'data': status_line}, broadcast=True)

        self.sessions[uid] = conn

    def remove_client(self, conn):
        client_uid = conn._conn._config['connid']

        to_delete = []
        for k, v in self.sessions.iteritems():
            session_uid = v._conn._config['connid']
            if client_uid == session_uid:
                to_delete.append(k)

        for session in to_delete:
            del(self.sessions[session])

    def sessions(self):
        return [{'id': id} for id in self.sessions.keys()]


class STListeners(STObject):
    def __init__(self):
        self.loaded = []

        if not self.loaded:
            self._scan()

    def _check(self, listener, path):
        attrs = ['name', 'author', 'description', 'listener_thread', 'options']

        for attr in attrs:
            if not hasattr(listener, attr):
                logging.error('Failed loading listener {}: missing {} attribute'.format(path, attr))
                return False

        return True

    def _load(self, listener_path):
        listener = imp.load_source('protocol', listener_path).Listener()
        if self._check(listener, listener_path):
            return listener

    def _scan(self):
        path = './listeners/'
        self.loaded = []
        for listener in os.listdir(path):
            if listener[-3:] == '.py' and listener[:-3] != '__init__':
                obj = self._load(os.path.join(path, listener))
                self.loaded.append(obj)

        logging.debug("Loaded {} listener(s) : {}".format(len(self.loaded), [lst.name for lst in self.loaded]))

    def running(self, data):
        return [{'name': lstr['Name'], 'host': lstr['Host'], 'bindip': lstr['BindIP'], 'port': lstr['Port']} for lstr in self.loaded if lstr.running]

    def available(self, data):
        return [{'name': lstr.name, 'description': lstr.description} for lstr in self.loaded]

    def use(self, data):
        listener_name = data['args'][0]

        for listener in self.loaded:
            if listener_name.lower() == listener.name.lower():
                return {'result': True, 'name': listener.name}

        return {'result': False}

    def set(self, data):
        listener_name = data['selected']
        key, value = data['args']

        if listener_name:
            for listener in self.loaded:
                if listener_name.lower() == listener.name.lower():
                    listener[key] = value
                    return {'result': True}

        return {'result': False}

    def options(self, data):
        listener_name = data['selected']

        if listener_name:
            for listener in self.loaded:
                if listener_name.lower() == listener.name.lower():
                    return [{k: v['Value']} for k, v in listener.options.iteritems()]
        return []

    def start(self, data):
        listener_name = data['selected']

        if listener_name:
            for listener in self.loaded:
                if listener_name.lower() == listener.name.lower():
                    listener.start_listener(STService)
                    return {'result': True}

        return {'result': False}

    def stop(self, data):
        listener_name = data['selected']

        if listener_name:
            for listener in self.loaded:
                if listener.running and listener['Name'] == listener_name:
                    listener.stop_listener()
                    return {'result': True}

        return {'result': False}


def jwt_required():
    with app.app_context():
        try:
            _jwt_required(app.config['JWT_DEFAULT_REALM'])
        except JWTError as e:
            logging.error(str(e))
            disconnect()
            abort(401)


class STNamespace(Namespace):
    def __init__(self, listeners, sessions, namespace=None):
        self.listeners = listeners
        self.sessions = sessions

        Namespace.__init__(self, namespace)

    def trigger_event(self, event, *args):
        try:
            event_name, method = event.lower().split('.')

            if not hasattr(self, event_name):
                return

            cl = getattr(self, event_name)
            if not method.startswith('_') and hasattr(cl, method):
                logging.debug('Calling {}.{}'.format(event_name, method))
                handler = lambda args: emit('response.{}.{}'.format(event_name.lower(), method), {'data': getattr(cl, method)(args)})
        except ValueError:
            handler_name = 'on_' + event

            if not hasattr(self, handler_name):
                # there is no handler for this event, so we ignore it
                return

            handler = getattr(self, handler_name)

        return self.socketio._handle_event(handler, event, self.namespace, *args)

    def on_connect(self):
        jwt_required()
        logging.debug('Client connected {} sid: {}'.format(current_identity, request.sid))
        emit('new_login', {'data': 'User {} has logged in!'.format(current_identity.username)}, broadcast=True)

    def on_disconnect(self):
        user = connected_users.get_user_from_sid(request.sid)
        logging.debug('Client disconnected {} sid: {}'.format(user, request.sid))
        try:
            connected_users.remove_user(user.sid)
        except AttributeError:
            pass


# validate API token before every request except for the login URI
@app.before_request
def check_token():
    """
    Before every request, check if a valid token is passed along with the request.
    """
    if request.path != '/api/auth':
        jwt_required()


@app.errorhandler(400)
def invalid_request(error):
    return make_response(jsonify({'error': 'Invalid Request'}), 400)


@app.errorhandler(401)
def access_denied(error):
    return make_response(jsonify({'error': 'Access Denied'}), 401)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not Found'}), 404)


if __name__ == '__main__':

    args = get_arguments()

    connected_users = ConnectedUsers()
    listeners = STListeners()
    sessions = STSessions()
    namespace = STNamespace(listeners, sessions)

    setattr(STService, 'sessions', sessions)

    socketio.on_namespace(namespace)
    socketio.run(app, host=args.ip, port=args.port)
