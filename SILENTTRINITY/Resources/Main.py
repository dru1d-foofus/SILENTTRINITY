# -*- coding: utf-8 -*-

#from __future__ import unicode_literals, print_function
import clr
import sys

#clr.AddReference("IronPython")
#clr.AddReference("IronPython.Modules")
#clr.AddReference("System.IO.Compression")
#clr.AddReference('Microsoft.Scripting')
clr.AddReference('System.Windows.Forms')
import System.Windows.Forms as WinForms
#from System.IO import MemoryStream
#from System.IO.Compression import ZipArchive, ZipArchiveMode
#from System.Net import WebClient
#from System.Threading import Thread, ThreadStart
#from IronPython.Hosting import Python

#content = WebClient().DownloadData('http://172.16.164.1:8000/stdlib.zip')
#stream = MemoryStream(content)


#script = """print 'test'"""

#execute(script)

WinForms.MessageBox.Show('pwned', 'test')
