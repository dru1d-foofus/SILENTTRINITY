from typing import Dict, List, Any
from core.events import NEW_LISTENER 
from core.loader import Loader
from multiprocessing import Process
from multiprocessing.connection import Client
from copy import deepcopy


class Listener:

    def __init__(self):
        self.name = ''
        self.author = ''
        self.description = ''
        self.running = False
        self.options = {}
        self.sessions = []
        self.__conn = None
        self.__thread = None

    def run(self):
        return

    def __run(self):
        self.__conn = Client(('localhost', 60000), authkey=b'silenttrinity')
        self.dispatch_event(NEW_LISTENER)
        self.run()

    def start(self):
        self.__thread = Process(target=self.__run, daemon=True)
        self.__thread.start()
        self.running = True

    def dispatch_event(self, event, msg):
        self.__conn.send((event, msg))

    def stop(self):
        self.__thread.kill()
        self.running = False

    def __getitem__(self, key):
        return self.options[key]['Value']

    def __setitem__(self, key, value):
        self.options[key]['Value'] = value

    def __json__(self):
        return {
            'name': self.name,
            "description": self.description,
            'options': self.options,
            'running': self.running
        }


class Listeners(Loader):

    def __init__(self):
        Loader.__init__(self)
        self.type = "listener"
        self.paths = ["listeners/"]
        self.listeners = []

        self.get_modules()

    def list(self, args: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'available': [l.__json__() for l in self.loaded],
            'running': [l.__json__() for l in self.listeners]
        }

    def start(self, args: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        for listener in self.loaded:
            if listener.name == data['name']:
                listener_copy = deepcopy(listener)
                listener_copy.options = data['options']
                listener_copy.start()
                self.listeners.append(listener_copy)
                return {'success': True, 'name': listener_copy["Name"]}
        return {'success': False}

    def stop(self, args: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        return

    def use(self, args: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        for listener in self.loaded:
            if listener.name == args[0]:
                return {'exists': True, 'name': listener.name, 'options': listener.options}

        return {'exists': False, 'name': args[0]}

    def options(self, args: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def __len__(self):
        return len(self.listeners)

    def __iter__(self):
        return (x for x in self.listeners)

    def __json__(self):
        return {}
