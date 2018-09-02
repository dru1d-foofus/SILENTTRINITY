# SILENTTRINITY

## Requirements

- TeamServer and Client require Python >= 3.7
- SILENTTRINITY implant requires .NET >= 4.5

## Notes

### .NET runtime support

The implant needs .NET 4.5 or greater due to the IronPython DLLs being compiled against .NET 4.0, also there is no `ZipArchive` .NET library prior to 4.5.

Reading the source for the [IronPython Compiler](https://github.com/IronLanguages/ironpython2/tree/master/Src/IronPythonCompiler) it seems like we can get around the first issue by directly generating IL code through IKVM (I still don't understand why this works). However this would require modifying the compiler to generate a completely new EXE stub (definitely feasible, just time consuming to find the proper IKVM API calls).

### C2 Comms

Currently the implant only supports C2 over HTTP 1.1, .NET 4.5 seems to have a native WebSocket library which makes implementing a WS C2 channel more than possible.

HTTP/2 support for .NET's `HttpClient` API is in the works, just not yet released.

The stager and teamserver design are very much "future proof" which should make implementing these C2 Channels pretty trivial when the time comes.

### COM Interop

http://ironpython.net/documentation/dotnet/dotnet.html#oleautomation-and-com-interop

Beautiful.

We could possibly leaverage this to use IE's COM object to do C2 ala [WSC2](https://github.com/Arno0x/WSC2)

Also shellcode injection via dynamic Office Macros.

### Python Standard Library

We technically could load/use IronPython's stdlib instead of calling C# APIs but this would require writing some "magic" dependency resolving code. 

Possibly could modify [httpimports](https://github.com/operatorequals/httpimport) to do this automagically.

