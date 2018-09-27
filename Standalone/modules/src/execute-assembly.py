from System.Reflection import Assembly
from System.Text import Encoding
from System import Array, Object, String, Convert, Console
from System.IO import StreamWriter, MemoryStream

encoded_assembly = "ASSEMBLY_BASE64"

assembly = Assembly.Load(Convert.FromBase64String(encoded_assembly))
args = Array[Object]([Array[String](["ARGS"])])

with MemoryStream() as ms:
    with StreamWriter(ms) as sw:
        Console.SetOut(sw)
        Console.SetError(sw)
        assembly.EntryPoint.Invoke(None, args)
        sw.Flush()
        buffer = ms.ToArray()
        print Encoding.UTF8.GetString(buffer, 0, buffer.Length)
