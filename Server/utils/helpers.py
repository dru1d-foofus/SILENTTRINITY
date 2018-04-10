import socket
import threading
import os
import sys
import netifaces


class KThread(threading.Thread):
    """
    A subclass of threading.Thread, with a kill() method.
    From https://web.archive.org/web/20130503082442/http://mail.python.org/pipermail/python-list/2004-May/281943.html
    """

    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run      # Force the Thread toinstall our trace.
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


def lhost():
    """
    Return the local IP.
    """

    if os.name != 'nt':
        import fcntl
        import struct

        def get_interface_ip(ifname):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                return socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR
                    struct.pack('256s', str(ifname[:15]))
                )[20:24])
            except IOError:
                return ''

    ip = ''

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        pass
    except:
        print "Unexpected error:", sys.exc_info()[0]
        return ip

    if (ip == '' or ip.startswith('127.')) and os.name != 'nt':
        interfaces = netifaces.interfaces()
        for ifname in interfaces:
            if "lo" not in ifname:
                try:
                    ip = get_interface_ip(ifname)
                    if ip != "":
                        break
                except:
                    print 'Unexpected error:', sys.exc_info()[0]
                    pass
    return ip
