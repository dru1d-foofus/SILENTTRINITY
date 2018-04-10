import logging
from utils.helpers import lhost, KThread
from rpyc.utils.server import ThreadedServer


class Listener:
    def __init__(self):
        self.name = 'tcp'
        self.author = '@byt3bl33d3r'
        self.description = 'tcp listener'

        self.listener_thread = None

        self.options = {
            # format:
            #   value_name : {description, required, default_value}

            'Name' : {
                'Description'   :   'Name for the listener.',
                'Required'      :   True,
                'Value'         :   'tcp'
            },
            'Host' : {
                'Description'   :   'Hostname/IP for staging.',
                'Required'      :   True,
                'Value'         :   "tcp://{}:{}".format(lhost(), 18861)
            },
            'BindIP' : {
                'Description'   :   'The IPv4/IPv6 address to bind to on the control server.',
                'Required'      :   True,
                'Value'         :   '0.0.0.0'
            },
            'Port' : {
                'Description'   :   'Port for the listener.',
                'Required'      :   True,
                'Value'         :   18861
            }
        }

    def get_option(self, name):
        return self.options[name]['Value']

    def start_listener(self, service):
        listener = ThreadedServer(
            service,
            hostname=self.get_option('BindIP'),
            port=self.get_option('Port'),
        )

        self.listener_thread = KThread(target=listener.start)
        self.listener_thread.start()

        logging.info("SSL listener started!")

    def stop_listener(self):
        self.listener_thread.kill()
