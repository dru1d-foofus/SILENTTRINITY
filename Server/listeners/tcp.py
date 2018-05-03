from core.listener import STListener
from core.utils.helpers import KThread
from rpyc.utils.server import ThreadedServer


class Listener(STListener):
    def __init__(self):
        STListener.__init__(self)
        self.name = 'tcp'
        self.author = '@byt3bl33d3r'
        self.description = 'tcp listener'

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
                'Value'         :   "tcp://{}:{}".format(self.args.ip, 18861)
            },
            'BindIP' : {
                'Description'   :   'The IPv4/IPv6 address to bind to on the control server.',
                'Required'      :   True,
                'Value'         :   self.args.ip
            },
            'Port' : {
                'Description'   :   'Port for the listener.',
                'Required'      :   True,
                'Value'         :   18861
            }
        }

    def start_listener(self, service):
        listener = ThreadedServer(
            service,
            hostname=self['BindIP'],
            port=self['Port'],
        )

        self.listener_thread = KThread(target=listener.start)
        self.listener_thread.setDaemon(True)
        self.listener_thread.start()
        self.running = True
