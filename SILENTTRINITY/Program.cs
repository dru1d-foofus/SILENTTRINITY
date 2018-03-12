using System;
using IronPython.Hosting;
using IronPython.Modules;
//using IronPython.Runtime;
using System.IO;
using System.Linq;
using System.Reflection;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Utils;
using System.Collections.Generic;
//using System.Diagnostics;
//using System.Windows.Forms;

namespace SILENTTRINITY
{

    public class Runtime
    {

        // https://mail.python.org/pipermail/ironpython-users/2012-December/016366.html
        // http://ironpython.net/blog/2012/07/07/whats-new-in-ironpython-273.html
        // https://blog.adamfurmanek.pl/2017/10/14/sqlxd-part-22/

        public dynamic CreateEngine()
        {
            ScriptRuntimeSetup setup = Python.CreateRuntimeSetup(GetRuntimeOptions());
            var pyRuntime = new ScriptRuntime(setup);
            ScriptEngine engineInstance = Python.GetEngine(pyRuntime);

            AddPythonLibrariesToSysMetaPath(engineInstance);

            return engineInstance;
        }

        public void AddPythonLibrariesToSysMetaPath(ScriptEngine engineInstance)
        {
            Assembly asm = GetType().Assembly;
            var resQuery =
                from name in asm.GetManifestResourceNames()
                where name.ToLowerInvariant().EndsWith(".zip")
                select name;
           string resName = resQuery.Single();
           Console.WriteLine("[*] Found embedded resource : {0}", resName);
           var importer = new ResourceMetaPathImporter(asm, resName);
           dynamic sys = engineInstance.GetSysModule();
           sys.meta_path.append(importer);
           sys.path.append(importer);
           //List metaPath = sys.GetVariable("meta_path");
           //metaPath.Add(importer);
           //sys.SetVariable("meta_path", metaPath);
        }

        private static IDictionary<string, object> GetRuntimeOptions()
        {
            var options = new Dictionary<string, object>();
            options["Debug"] = false;
            return options;
        }

        static void Main()
        {

                Runtime runtime = new Runtime();
                var myScript = (string)null;

                try
                {

                    myScript = new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("SILENTTRINITY.Resources.Main.py")).ReadToEnd();

                }
                catch
                {
                    Console.WriteLine("[-] Error accessing resources, dumping available resources:");
                    string[] resourceNames = Assembly.GetExecutingAssembly().GetManifestResourceNames();
                    foreach (string resourceName in resourceNames)
                    {
                        Console.WriteLine(resourceName);
                    }

                }

                ScriptEngine engine = runtime.CreateEngine();
                engine.Execute(myScript);

        }
    }
}