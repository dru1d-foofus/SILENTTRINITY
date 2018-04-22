#! /usr/bin/env python2.7

from __future__ import unicode_literals, print_function
#import rpyc
#import sys
from flask import Flask, make_response, jsonify, abort, request, session
from flask_socketio import SocketIO, emit, disconnect
from flask_jwt import JWT, jwt_required, current_identity
from flask.json import JSONEncoder
from werkzeug.security import safe_str_cmp
from uuid import uuid4
#import threading
from rpyc.core import Service
import flask
import logging
import json
import os
import imp
import traceback
import zlib
import string
import random
#import marshal
#from IPython import embed
import sys


logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


def gen_secret_key():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(40))


class User(object):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def __str__(self):
        return "User(id='%s')" % self.id


users = [
    User(1, 'admin', 'admin'),
]


username_table = {u.username: u for u in users}
userid_table = {u.id: u for u in users}


def authenticate(username, password):
    user = username_table.get(username, None)
    if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
        logging.debug('Client authenticated successfully')
        return user

    logging.debug('Client failed authentication')


def identity(payload):
    user_id = payload['identity']
    return userid_table.get(user_id, None)


class MyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, STObject):
            return obj.toJson()

        return super(MyJSONEncoder, self).default(obj)


app = Flask(__name__)
app.config['SECRET_KEY'] = gen_secret_key()
app.config['JWT_AUTH_URL_RULE'] = '/api/auth'
app.json_encoder = MyJSONEncoder
jwt = JWT(app, authenticate, identity)
socketio = SocketIO(app, json=flask.json)


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
            self.sessions.add_client(self)

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
    def toJson(self):
        return json.dumps(self.__dict__)

    def __repr__(self):
        return self.toJson()


class STSessions(STObject):
    def __init__(self):
        self.sessions = {}

    def add_client(self, conn):

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

        print(client_infos)

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


class STListeners(STObject):
    def __init__(self):
        self.available = []
        self.selected = None

        if not self.available:
            self.scan()

    def check(self, listener, path):
        attrs = ['name', 'author', 'description', 'listener_thread', 'options']

        for attr in attrs:
            if not hasattr(listener, attr):
                logging.error('Failed loading listener {}: missing {} attribute'.format(path, attr))
                return False

        return True

    def load(self, listener_path):
        listener = imp.load_source('protocol', listener_path).Listener()
        if self.check(listener, listener_path):
            return listener

    def scan(self):
        path = './listeners/'
        self.available = []
        for listener in os.listdir(path):
            if listener[-3:] == '.py' and listener[:-3] != '__init__':
                obj = self.load(os.path.join(path, listener))
                self.available.append(obj)

        logging.debug("Loaded {} listener(s) : {}".format(len(self.available), [lst.name for lst in self.available]))

    def toJson(self):
        return {
            'available': [{'Name': lstr.name, 'Description': lstr.description} for lstr in self.available],
            'running': []  # TO DO
        }


@app.route('/api/listeners', methods=['GET'])
def get_listeners():
    return make_response(jsonify({'response': listeners}))


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    return make_response(jsonify({'response': sessions}))


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


@socketio.on('sessions')
@jwt_required()
def ws_get_sessions(message):
    emit('response', {'data': sessions})


@socketio.on('listeners')
@jwt_required()
def ws_get_listeners(message):
    emit('response', {'data': listeners})

#@socketio.on_error_default
#def default_error_handler(e):
#    logging.error('Error')
#    print(request.event["message"])  # "my error event"
#    print(request.event["args"])     # (data,)


@socketio.on('connect')
@jwt_required()
def connect_handler():
    logging.info('Client connected: {}'.format(request.sid))


@socketio.on('disconnect')
def disconnect_handler():
    logging.info('Client disconnected: {}'.format(request.sid))


if __name__ == '__main__':
    listeners = STListeners()
    sessions = STSessions()
    setattr(STService, 'sessions', sessions)

    socketio.run(app, port=5000)
