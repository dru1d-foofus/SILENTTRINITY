import functools
import core.state as state
from time import gmtime, strftime
from queue import Queue, Empty
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import WordCompleter
from core.utils import command, print_info, print_good
from core.events import NEW_SESSION, SESSION_STAGED, SESSION_CHECKIN, NEW_JOB
from core.ipcserver import ipc_server
from terminaltables import AsciiTable

class Sessions:
    def __init__(self, prompt_session):
        self.name = 'sessions'
        self.prompt = HTML('ST (<ansired>sessions</ansired>) ≫ ')
        self.completer = WordCompleter(['list', 'listeners', 'modules', 'exit'])
        self.prompt_session = prompt_session

        self.sessions = []

        ipc_server.attach(NEW_SESSION, self.__add_session)
        ipc_server.attach(SESSION_STAGED, self.__notify_session_staged)
        ipc_server.attach(SESSION_CHECKIN, self.__session_checked_in)
        ipc_server.attach(NEW_JOB, self.__add_job)

    def __add_session(self, session_obj):
        print_good(f"New session {session_obj.guid} connected! ({session_obj.address})")
        # We can't pickle an object with a queue, so we need to add it after we receive it. Ugly.
        session_obj.queue = Queue()
        self.sessions.append(session_obj)
        state.SESSIONS = len(self.sessions)

    def __notify_session_staged(self, msg):
        print_info(msg)

    def __session_checked_in(self, guid):
        for session in self.sessions:
            if session.guid == guid:
                session.checked_in()
                try:
                    return session.queue.get(block=False)
                except Empty:
                    return

    def __add_job(self, job_tuple):
        guid, job = job_tuple
        for session in self.sessions:
            if session.guid == guid:
                session.add_job(job)

    @command
    def list(self, guid: str):
        """
        Get available sessions

        Usage: list [<guid>] [-h]

        Arguments:
            guid  filter by session's guid
        """

        table_data = [
            ["GUID", "Address", "Last Checkin"]
        ]
        for session in self.sessions:
            table_data.append([
                session.guid, 
                session.address, 
                strftime("h %H m %M s %S", gmtime(session.last_check_in()))
            ])

        table = AsciiTable(table_data)
        print(table.table)
