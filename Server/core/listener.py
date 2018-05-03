from core.arguments import get_arguments
from core.utils.helpers import STObject


class STListener(STObject):
    def __init__(self):
        self.name = ''
        self.author = ''
        self.description = ''

        self.running = False
        self.listener_thread = None
        self.args = get_arguments()

        self.options = {
            # format:
            #   value_name : {description, required, default_value}
        }

    def start_listener(self, service):
        pass

    def stop_listener(self):
        self.listener_thread.kill()
        self.running = False

    def __getitem__(self, key):
        return self.options[key]['Value']

    def __setitem__(self, key, value):
        self.options[key]['Value'] = value
