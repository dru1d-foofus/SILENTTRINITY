import netifaces
import random
import string
from base64 import b64decode


def gen_random_string(length=8):
    return ''.join(random.sample(string.ascii_letters, int(length)))


def get_interfaces():
    return netifaces.interfaces()


def get_ipaddress(interface=None):
    if interface and (interface in get_interfaces()):
        return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
    else:
        for iface in ['eth0', 'en0', 'lo0']:
            try:
                return netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
            except (ValueError, KeyError):
                continue

            return ""


def decode_auth_header(request_headers):
    auth_header = request_headers['Authorization']
    auth_header = b64decode(auth_header)
    username, password_digest = auth_header.decode().split(':')
    return username, password_digest
