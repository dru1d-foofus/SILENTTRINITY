import clr
clr.AddReference("System.Management")
clr.AddReference("System.Management.Automation")
from System.Reflection import Assembly
from System.Management.Automation import *
from System.Management.Automation.Host import *
from System.Management.Automation.Runspaces import *
from System.Management.Automation.Runspaces import RunspaceFactory


class PowerShellWrapper:
    def __init__(self, alias=lambda x: x.replace('^', '$')):
        self.runspace = RunspaceFactory.CreateRunspace()
        self.runspace.Open()
        self.ri = RunspaceInvoke(self.runspace)
        self.output = []
        self._alias = alias

    def include(self, files=[]):
        for fl in files:
            self.cmd(open(fl).read())
        return self

    # run q and fill output
    def cmd(self, q):
        self.output = self.ri.Invoke(self._alias(q))
        return self

    # try convert output to string
    def toStr(self):
        return "".join([str(i) for i in self.output])

    def out(self):
        return [[[k, getattr(i.ImmediateBaseObject, k)] for k in dir(i.ImmediateBaseObject) if i.ImmediateBaseObject.GetType().GetProperty(k) and hasattr(i.ImmediateBaseObject, k)] +
                [[k.Name, i.ImmediateBaseObject.GetAttribute(k.Name)] for k in i.ImmediateBaseObject.Attributes if hasattr(i.ImmediateBaseObject, "Attributes")] for i in self.output]
