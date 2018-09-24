import hmac
import logging
from typing import get_type_hints, List, Dict
from functools import wraps
from docopt import docopt
from shlex import split
from base64 import b64encode
from hashlib import sha512
from termcolor import colored
from websockets.http import Headers


class CmdError(Exception):
    pass


def command(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cmd_args = docopt(func.__doc__.strip(), argv=args[1])
        validated_args = {}
        for name, hint in get_type_hints(func).items():
            try:
                value = cmd_args[f'<{name}>']
            except KeyError:
                try:
                    value = cmd_args[f'--{name}']
                except KeyError:
                    raise CmdError(f"Unable to find '{name}' argument in command definition")

            try:
                validated_args[name] = hint(value)
            except TypeError:
                # I'm still not sure if there's a way to dynamically cast Lists and Dicts using type hints
                if hint == List[int]:
                    validated_args[name] = [int(x) for x in value]
                elif hint == List[str]:
                    validated_args[name] = [str(x) for x in value]
                else:
                    raise NotImplemented(f"Casting for type '{hint}' has not been implemented")

        return func(args[0], **validated_args)
    return wrapper


def generate_auth_header(username, password):
    client_digest = hmac.new(password.encode(), msg=b'silenttrinity', digestmod=sha512).hexdigest()
    header_value = b64encode(f"{username}:{client_digest}".encode()).decode()
    return Headers({'Authorization': header_value})


def print_good(msg):
    print(f"{colored('[+]', 'green')} {msg}")


def print_bad(msg):
    print(f"{colored('[-]', 'red')} {msg}")


def print_info(msg):
    print(f"{colored('[*]', 'blue')} {msg}")
