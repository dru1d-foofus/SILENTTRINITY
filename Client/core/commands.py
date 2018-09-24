import asyncio
import functools
import websockets
import logging
import json
import core.state as client_state
from docopt import DocoptExit
from shlex import split
from core.utils import command, print_bad, print_good, print_info
from terminaltables import AsciiTable
from prompt_toolkit import PromptSession
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.styles import Style

use_asyncio_event_loop()

example_style = Style.from_dict({
    'rprompt': 'bg:#ff0066 #ffffff',
})

def bottom_toolbar():
    if client_state.CONNECTED:
        return HTML(f"{client_state.USERNAME}@{client_state.HOST}:{client_state.PORT} (Sessions: {client_state.SESSIONS} Users: {client_state.USERS} Listeners: {client_state.LISTENERS})")
    else:
        return HTML('<b><style bg="ansired">Disconnected</style></b>')


def get_rprompt(error=False):
    return ' Error ' if error else ''


class UserExit(Exception):
    pass


class Sessions:
    def __init__(self, websocket, prompt_session):
        self.name = 'sessions'
        self.prompt = HTML('ST (<ansired>sessions</ansired>) ≫ ')
        self.completer = WordCompleter(['listeners', 'modules', 'options', 'events', 'users', 'server', 'exit', 'list'])
        self.websocket = websocket
        self.prompt_session = prompt_session

    @command
    def list(self, guid: str):
        """
        Get available sessions

        Usage: list [<guid>] [-h]

        Arguments:
            guid  filter by session's guid
        """

        print('wat')


class Listeners:
    def __init__(self, websocket, prompt_session):
        self.name = 'listeners'
        self.prompt = HTML('ST (<ansired>listeners</ansired>) ≫ ')
        self.completer = WordCompleter(['sessions', 'modules', 'options', 'events', 'users', 'server', 'exit', 'list'])
        self.websocket = websocket
        self.prompt_session = prompt_session
        self.selected_listener = ''
        self.listener_options = None

    @command
    def list(self, name: str):
        """
        Get running/available listeners

        Usage: list [<name>] [-h]

        Arguments:
            name  filter by listener name
        """

    def list_result(self, result):

        available_table_data = [
            ["Name", "Description"]
        ]

        running_table_data = [
            ["Name", "Description"]
        ]

        for l in result['available']:
            available_table_data.append([l["name"], l["description"]])

        for l in result['running']:
            running_table_data.append([l["name"], l["description"]])

        atable = AsciiTable(available_table_data, title="Available")
        rtable = AsciiTable(running_table_data, title="Running")
        print(atable.table)
        print()
        print(rtable.table)

    @command
    def set(self, key: str, value: str):
        """
        Set options on the selected listener

        Usage: set <key> <value> [-h]

        Arguments:
            name  filter by listener name
        """

        if self.listener_options:
            try:
                self.listener_options[key]['Value'] = value
            except KeyError:
                print_bad(f"Unknown option '{key}'")

    def start(self, args):
        """
        Start the selected listener
        """

        if self.selected_listener and self.listener_options:
            return {'name': self.selected_listener, 'options': self.listener_options}

    def start_result(self, result):
        if result['success'] is True:
            print_good(f"Listener '{result['name']}' started successfully!")

    @command
    def use(self, name: str):
        """
        Select the specified listener

        Usage: use <name> [-h]

        Arguments:
            name  filter by listener name
        """

    def use_result(self, result):
        if result['exists'] is True:
            self.prompt = HTML(f"ST (<ansired>listeners</ansired>)(<ansired>{result['name']}</ansired>) ≫ ")
            self.selected_listener = result['name']
            self.listener_options = result['options']
        elif result['exists'] is False:
            print_bad(f"Listener '{result['name']}' does not exist")

    @command
    def options(self, name: str):
        """
        Get selected listener options

        Usage: options [<name>] [-h]

        Arguments:
            name  filter by listener name
        """

        if self.listener_options:
            table_data = [
                ["Option Name", "Required", "Value", "Description"]
            ]

            for k, v in self.listener_options.items():
                table_data.append([k, v["Required"], v["Value"], v["Description"]])

            table = AsciiTable(table_data)
            table.inner_row_border = True
            print(table.table)


class MainCmdLoop:
    def __init__(self, websocket):
        self.name = 'main'
        self.websocket = websocket
        self.completer = WordCompleter(['listeners', 'sessions', 'modules', 'options', 'events', 'users', 'server', 'exit'], ignore_case=True)

        self.prompt_session = PromptSession(
            'ST ≫ ',
            bottom_toolbar=bottom_toolbar,
            completer=self.completer,
            auto_suggest=AutoSuggestFromHistory(),
            rprompt=get_rprompt(False),
            style=example_style,
        )

        self.contexts = [
            Listeners(self.websocket, self.prompt_session),
            Sessions(self.websocket, self.prompt_session),
        ]

        self.current_context = self

    def switched_context(self, result):
        for ctx in self.contexts:
            if result == ctx.name:
                self.prompt_session.message = ctx.prompt
                self.prompt_session.completer = ctx.completer
                self.current_context = ctx
                return True
        return False

    def get_context(self, ctx_name):
        for ctx in self.contexts:
            if ctx_name == ctx.name:
                return ctx

    async def run_resource_file(self):
        with open(client_state.args['--resource-file']) as resource_file:
            for cmd in resource_file:
                with patch_stdout():
                    result = await self.prompt_session.prompt(accept_default=True, default=cmd.strip(), async_=True)

    async def __call__(self):
        while True:
            with patch_stdout():
                result = await self.prompt_session.prompt(async_=True)
                if len(result):
                    if result == 'exit':
                        break

                    if not self.switched_context(result):
                        command = split(result)
                        try:
                            logging.info(f"command: {command[0]} args: {command[1:]} ctx: {self.current_context.name}")

                            data = getattr(self.current_context, command[0])(command[1:])
                            if hasattr(self.current_context, f"{command[0]}_result"):
                                await self.websocket.send(json.dumps({
                                    "ctx": self.current_context.name,
                                    "cmd": command[0],
                                    "args": command[1:],
                                    "data": {} if not data else data
                                }))

                        except AttributeError:
                            print_bad(f"Unknown command '{command[0]}'")
                        except DocoptExit as e:
                            print(str(e))
                        except SystemExit:
                            pass
                        except websockets.exceptions.ConnectionClosed as e:
                            logging.error(e)
                            logging.error("Disconnected from teamserver")
                            client_state.CONNECTED = False
