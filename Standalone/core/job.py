from core.utils import gen_random_string
from base64 import b64encode

class Job:

    def __init__(self, module):
        self.id = gen_random_string()
        self.module = module

    def json(self):
        data = b64encode(self.module.payload()).decode()
        return {'id': self.id, 'command': 'run_script', 'args': self.module.options, 'data': data}
