from core.module import STModule


class Module(STModule):
    def __init__(self):
        self.name = 'powershell'
        self.description = 'Execute arbitrary PowerShell in an un-managed runspace'
        self.author = '@byt3bl33d3r'

    def options(self):
        pass

    def payload(self):
        pass
