class STModule:
    def __init__(self):
        self.name = 'powershell'
        self.description = 'Execute arbitrary PowerShell in an un-managed runspace'
        self.author = '@byt3bl33d3r'
        self.options = {}

    def options(self):
        return

    def payload(self):
        return