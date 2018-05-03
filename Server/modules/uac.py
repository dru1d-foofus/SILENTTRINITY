from core.module import STModule


class Module(STModule):
    def __init__(self):
        self.name = 'uac'
        self.description = 'Checks UAC level'
        self.author = '@byt3bl33d3r'

    def options(self):
        pass

    def payload(self):
        pass
