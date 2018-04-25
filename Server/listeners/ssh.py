import paramiko
from core.arguments import get_arguments
from utils.helpers import KThread
from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import AuthenticationError

# This should work in theory?
# https://github.com/paramiko/paramiko/blob/master/demos/demo_server.py


class SSHServer(paramiko.ServerInterface):
    def get_allowed_auths(self, username):
        return 'password,publickey'


class SSHAuthenticator(object):

    def __init__(self, keyfile, username='st', password=None):
        self.keyfile = keyfile
        self.username = username
        self.password = password
        self.host_key = paramiko.RSAKey(filename='test_rsa.key')

        # To Do

    def __call_(self, sock):
        t = paramiko.Transport(sock)
        t.add_server_key(self.host_key)
        server = SSHServer()
        t.start_server(server=server)

        try:
            t.accept(20)
        except Exception as e:
            raise AuthenticationError(str(e))

        return t.socket, None


class Listener:
    def __init__(self):
        self.name = 'ssh'
        self.author = '@byt3bl33d3r'
        self.description = 'ssh listener'

        self.running = False
        self.listener_thread = None
        self.args = get_arguments()

        self.options = {
            # format:
            #   value_name : {description, required, default_value}

            'Name' : {
                'Description'   :   'Name for the listener.',
                'Required'      :   True,
                'Value'         :   'ssh'
            },
            'Host' : {
                'Description'   :   'Hostname/IP for staging.',
                'Required'      :   True,
                'Value'         :   "ssh://{}:{}".format(self.args.ip, 22)
            },
            'BindIP' : {
                'Description'   :   'The IPv4/IPv6 address to bind to on the control server.',
                'Required'      :   True,
                'Value'         :   self.args.ip
            },
            'Port' : {
                'Description'   :   'Port for the listener.',
                'Required'      :   True,
                'Value'         :   22
            }
        }

    def start_listener(self, service):
        listener = ThreadedServer(
            service,
            hostname=self['BindIP'],
            port=self['Port'],
            authenticator=SSHAuthenticator
        )

        self.listener_thread = KThread(target=listener.start)
        self.listener_thread.setDaemon(True)
        self.listener_thread.start()
        self.running = True

    def stop_listener(self):
        self.listener_thread.kill()
        self.running = False

    def __getitem__(self, key):
        return self.options[key]['Value']

    def __setitem__(self, key, value):
        self.options[key]['Value'] = value
