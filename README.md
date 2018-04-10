# SILENTTRINITY


# Roadmap features & Notes

## Modular C2 system
A must, would be great to base it off of Cobalt Strike's malleable C2 system.

## Client/Server architecture & minimalistic GUI
Since the server's console UI is based off of IPython, we can take advantage of this and create an optional client/server architecture (a.k.a teamserver) using it's kernel.

- https://stackoverflow.com/questions/9977446/connecting-to-a-remote-ipython-instance

API has changed a bit since that article, from the little reasearch I did it seems that all that is needed server side is:

```python
from IPython.kernel import KernelManager

k = KernelManager()
k.start_kernel()

k.connection_file  # Generated on the fly, need to supply to client to connect
```

The beauty of this is, since everyone connecting to this instance would share the same kernel, IPython would implicitly act as a teamserver!

You can even connect to it with IPython's/Jupyter's [QT Interface](https://ipython.org/ipython-doc/3/interactive/qtconsole.html), which would give it an insanely cool/minimilistic GUI interface straight out of the box.

I still have to figure out a way of passing the custom magic commands & prompt of the server to the actual kernel, there obviously is a way of doing this, IPython's documentation is *extremely* lackluster when it comes to this feature not suprisingly so some digging will have to be done inside the code.

# Pivoting
RPyc makes this insanely easy https://rpyc.readthedocs.io/en/latest/docs/howto.html#tunneling

# P2P comms 
RPyC to the rescue again https://rpyc.readthedocs.io/en/latest/docs/servers.html#registry-server

Incredibly enough, it **already** has support for [SMB named pipe comms](https://rpyc.readthedocs.io/en/latest/api/core_stream.html#rpyc.core.stream.NamedPipeStream), only problem is that it's current implementation requires pywin32, which is a CPython extension (IronPython can't run those, maybe we can pull of the same API calls with ctypes?).

I'm sure we can base our own off of these:
- https://github.com/threatexpress/invoke-pipeshell
- https://github.com/FuzzySecurity/PowerShell-Suite/blob/master/Invoke-SMBShell.ps1
