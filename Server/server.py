from rpyc.core import Service
from rpyc.utils.server import ThreadedServer
from IPython import embed
#import rpyc
#import sys
import logging
import json
import traceback
import zlib

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


class SILENTTRINITY(Service):
    def on_connect(self):
        logging.info("[+] New client connected: {}".format(self._conn._config["endpoints"][1]))

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
            '''
            try:
                self.namespace = self._conn.root.namespace
            except Exception:
                if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                    raise
                else:
                    return
            '''
        except Exception as e:
            logging.error("Caught error when receiving connection: {}".format(e))
            logging.error(traceback.format_exc())

        embed()

    def on_disconnect(self):
        logging.info("[*] Client disconnected")

    def exposed_set_modules(self, modules):
        self.modules = modules

    def exposed_json_dumps(self, js, compressed=False):
        data = json.dumps(js)
        if compressed:
            data = zlib.compress(data)

        return data


if __name__ == "__main__":
    t = ThreadedServer(SILENTTRINITY, port=18861)
    t.daemon = True
    t.start()
