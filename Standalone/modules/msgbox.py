class STModule:
    def __init__(self):
        self.name = 'msgbox'
        self.description = 'Pop a message box'
        self.author = '@byt3bl33d3r'
        self.options = {}

    def options(self):
        pass

    def payload(self):
        with open('modules/src/msgbox.py', 'rb') as module_src:
            return module_src.read()
