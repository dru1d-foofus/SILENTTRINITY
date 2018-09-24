import logging
import asyncio
from multiprocessing.connection import Listener
from threading import Thread


class ThreadedEventListener(Thread):
    """
    This is (sort of?) a barebones implementation of a reverse pub/sub
    pattern: multiple publishers can connect to this and it dispatches
    the events to registered subscribers.

    Why? Cause miss me with that zeromq shit.
    """

    def __init__(self, loop, address=('localhost', 60000), authkey=b'silenttrinity'):
        Thread.__init__(self)
        self.loop = loop
        self.name = 'EventListener'
        self.address = address
        self.listener = Listener(self.address, authkey=authkey)
        self.daemon = True
        self.subscribers = {}

    def run(self):
        logging.debug(f"Started IPC server on {self.address}")
        while True:
            client = self.listener.accept()

            t = Thread(target=self.serve, args=(client,))
            t.setDaemon(True)
            t.start()

    def attach(self, event, func):
        if event not in self.subscribers:
            self.subscribers[event] = set()
            self.subscribers[event].add(func)
        else:
            self.subscribers[event].add(func)
    
    def detach(self, event, func):
        raise NotImplemented
    
    def publish(self, msg):
        for k, v in self.subscribers.items():
            for func in v:
                asyncio.run_coroutine_threadsafe(func(msg), loop=self.loop)

    def serve(self, client):
        logging.debug(f"connection accepted from {self.listener.last_accepted}")
        while True:
            try:
                data = client.recv()
            except EOFError:
                pass

            topic, msg = data
            logging.debug(f"Got event: {topic} msg: {msg}")
            if topic in self.subscribers:
                for sub in self.subscribers[topic]:
                    asyncio.run_coroutine_threadsafe(sub(msg), loop=self.loop)
            else:
                logging.debug(f"Got event: {topic}, but there's nothing subscribed")
