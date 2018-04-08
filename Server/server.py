#! /usr/bin/env python2.7

#import rpyc
#import sys
import logging
import json
import traceback
import zlib
#import threading
from rpyc.core import Service
from rpyc.utils.server import ThreadedServer
from IPython.core.magic import (Magics, magics_class, line_magic)
#from IPython.core.autocall import IPyAutocall
from IPython.terminal.prompts import Prompts, Token
from IPython.terminal.embed import InteractiveShellEmbed

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


class STPrompt(Prompts):

    def __init__(self, shell, **kwargs):
        super(STPrompt, self).__init__(shell, **kwargs)
        self.val = None

    def in_prompt_tokens(self, cli=None):
        if self.val is None:
            return [(Token, "["), (Token.PromptNum, str(
                self.shell.execution_count)), (Token, "] ST"), (Token.Prompt, " > ")]
        else:
            return [
                (
                    Token, "["), (Token.PromptNum, str(
                        self.shell.execution_count)), (Token, "] ST("), (Token.PromptNum, "%x" %
                                                                            self.val), (Token, ")"), (Token.Prompt, " > ")]

    def continuation_prompt_tokens(self, cli=None, width=None):
        if width is None:
            width = self._width()
        return [(Token.Prompt, (' ' * (width - 2)) + u' > '), ]

    def out_prompt_tokens(self):
        width = self._width()
        spaces = width - 7 - len(str(self.shell.execution_count))
        return [(Token, "["), (Token.PromptNum, str(self.shell.execution_count)),
                (Token, "]" + " " * spaces + "  "), (Token.Prompt, " > ")]

    def set_proc(self, proc):
        self.val = proc


class STService(Service):

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

        shell()

    def on_disconnect(self):
        logging.info("[*] Client disconnected")

    def exposed_set_modules(self, modules):
        self.modules = modules

    def exposed_json_dumps(self, js, compressed=False):
        data = json.dumps(js)
        if compressed:
            data = zlib.compress(data)

        return data


@magics_class
class STShellMagics(Magics):
    def __init__(self, shell=None, **kwargs):
        super(STShellMagics, self).__init__(shell=shell, **kwargs)

    @line_magic
    def this_is_a_custom_command(sef, line):
        return

if __name__ == "__main__":
    shell = InteractiveShellEmbed(banner1="", exit_msg="")
    shell.register_magics(STShellMagics)
    prompt = STPrompt(shell)
    shell.prompts = prompt

    server = ThreadedServer(STService, port=18861)
    server.daemon = True
    server.start()
    #t = threading.Thread(target=server.start)
    #t.setDaemon(True)
    #t.start()
