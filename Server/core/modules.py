from core.loader import Loader


class Module(object):
    def __init__(self):
        self.name = ''
        self.author = ''
        self.description = ''

    def options(self):
        pass

    def payload(self):
        pass


class Modules(Loader):

    def list(self):
        return
