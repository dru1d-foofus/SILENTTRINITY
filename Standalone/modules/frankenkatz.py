class STModule:
    def __init__(self):
        self.name = 'frankenkatz'
        self.description = 'Creates a minidump of LSASS via Win32 API Calls and loads Mimikatz in memory using dynamic CSharp compilation through the PyDLR'
        self.author = '@byt3bl33d3r'
        self.options = {}

    def options(self):
        pass

    def payload(self):
        with open('modules/src/frankenkatz.py', 'rb') as module_src:
            return module_src.read()
