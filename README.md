# SILENTTRINITY


# Roadmap features & Notes

## Modular C2 system
A must, would be great to base it off of Cobalt Strike's malleable C2 system.

## Client/Server architecture & minimalistic GUI
~~Since the server's console UI is based off of IPython, we can take advantage of this and create an optional client/server architecture (a.k.a teamserver) using it's kernel.~~

Having done some pretty extensive research on this, it seems IPython was just not meant for creating complex CLI's. Thankfully, the actual "bells and whistles" of the IPython interpreter are provided by the `prompt_toolkit` library.

I already started re-writing the CLI using it, there are two main downfalls in using `prompt_toolkit`:

1. Docs are only available for the bleeding edge version (2.0) which is only on Github and not on PyPi.
2. Since IPython uses `prompt_toolkit` v1.0, installing v2.0 in the same virtualenv breaks IPython (which means we can't use `embed()` for debugging purposes. *Huge* pain in the ass.)


Overall though, `prompt_toolkit` provides much greater flexibility.

I also started working on the client/server architecture. Initially, I was just going to go with a standard HTTP REST API using Flask, however, after thinking about some potential use cases and limitations that this would cause I thought it would make more sense to use websockets. This would allow the client to update and receive data in realtime which is pretty bad ass.

Thankfully, Flask already has a [websocket addon package](https://github.com/miguelgrinberg/Flask-SocketIO), which makes this pretty straight forward!

# Pivoting
RPyc makes this insanely easy https://rpyc.readthedocs.io/en/latest/docs/howto.html#tunneling

# P2P comms
RPyC to the rescue again https://rpyc.readthedocs.io/en/latest/docs/servers.html#registry-server

Incredibly enough, it **already** has support for [SMB named pipe comms](https://rpyc.readthedocs.io/en/latest/api/core_stream.html#rpyc.core.stream.NamedPipeStream), only problem is that it's current implementation requires pywin32, which is a CPython extension (IronPython can't run those, maybe we can pull of the same API calls with ctypes?).

I'm sure we can base our own off of these:
- https://github.com/threatexpress/invoke-pipeshell
- https://github.com/FuzzySecurity/PowerShell-Suite/blob/master/Invoke-SMBShell.ps1
