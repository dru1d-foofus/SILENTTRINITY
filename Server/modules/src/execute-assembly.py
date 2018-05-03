import clr
clr.AddReference('System')
import System
from System import Array
from System.Reflection import Assembly

args = Array[System.Object]([Array[System.String](['-FirstArg', 'Value', '-SecondArg', 'Value'])])

assembly = 'base64d assembly'

# Need a way to detect args of Main()
asm = Assembly.Load("")
asm.Entrypoint.Invoke(None, args)
