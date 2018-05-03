from core.module import STModule


class Module(STModule):
    def __init__(self):
        self.name = 'execute-assembly'
        self.description = 'Execute a .NET assembly in memory'
        self.author = '@byt3bl33d3r'

    def options(self):
        pass

    def payload(self):
        pass
