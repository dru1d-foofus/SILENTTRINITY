using System;
using IronPython.Hosting;
using IronPython.Modules;
//using IronPython.Runtime;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using Microsoft.Scripting.Hosting;
//using Microsoft.Scripting.Utils;
using System.Collections.Generic;

namespace SILENTTRINITY
{

    public class Runtime
    {

        // https://mail.python.org/pipermail/ironpython-users/2012-December/016366.html
        // http://ironpython.net/blog/2012/07/07/whats-new-in-ironpython-273.html
        // https://blog.adamfurmanek.pl/2017/10/14/sqlxd-part-22/

        public dynamic CreateEngine()
        {
            ScriptRuntimeSetup setup = Python.CreateRuntimeSetup(options: GetRuntimeOptions());
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
                where name.ToLowerInvariant().Equals("stdlib.zip")
                select name;
            try
            {
                string resName = resQuery.Single();
                Console.WriteLine("Found Python embedded stdlib: {0}", resName);
                var importer = new ResourceMetaPathImporter(asm, resName);
                dynamic sys = engineInstance.GetSysModule();
                sys.meta_path.append(importer);
                sys.path.append(importer);
                //List metaPath = sys.GetVariable("meta_path");
                //metaPath.Add(importer);
                //sys.SetVariable("meta_path", metaPath);
            }
            catch
            {
                Console.WriteLine("Could not find Python embedded stdlib");
            }
        }

        private IDictionary<string, object> GetRuntimeOptions()
        {
            var options = new Dictionary<string, object>
            {
                ["Debug"] = false
            };
            return options;
        }

        public static void DumpEmbeddedResources()
        {
            Console.WriteLine("Available embedded resources:");
            string[] resourceNames = Assembly.GetExecutingAssembly().GetManifestResourceNames();
            foreach (string resourceName in resourceNames)
            {
                Console.WriteLine("\t {0}", resourceName);
            }
            Console.WriteLine();
        }

        public static Byte[] GetAssemblyInZip(ZipArchive zip, string assemblyName)
        {
            Byte[] assemblyData = new Byte[0];

            foreach (var entry in zip.Entries)
            {
                if (entry.Name == assemblyName + ".dll")
                {
                    Console.WriteLine("Found {0}.dll in embedded resource zip file\n", assemblyName);
                    using (var dll = entry.Open())
                    {
                        assemblyData = new Byte[entry.Length];
                        dll.Read(assemblyData, 0, assemblyData.Length);
                        return assemblyData;
                    }
                }
            }
            return assemblyData;
        }

        public static void Main(string[] args)
        {

            DumpEmbeddedResources();
            String resourceZipFile = "SILENTTRINITY.Resources.dlls.zip";

            ZipArchive zip = new ZipArchive(Assembly.GetExecutingAssembly().GetManifestResourceStream(resourceZipFile), ZipArchiveMode.Read);

            AppDomain.CurrentDomain.AssemblyResolve += (sender, resourceargs) =>
            {
                String assemblyName = new AssemblyName(resourceargs.Name).Name;
                Console.WriteLine("Trying to resolve {0}", assemblyName);

                return Assembly.Load(GetAssemblyInZip(zip, assemblyName));
            };

            CreateRuntime();
        }

        public static void CreateRuntime()
        {
            Runtime runtime = new Runtime();

            string myScript = new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("SILENTTRINITY.Resources.Main.py")).ReadToEnd();
            ScriptEngine engine = runtime.CreateEngine();
            engine.Execute(myScript);

        }
    }
}