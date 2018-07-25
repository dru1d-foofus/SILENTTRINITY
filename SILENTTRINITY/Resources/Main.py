# -*- coding: utf-8 -*-

#from __future__ import unicode_literals, print_function
import clr
import sys
import logging
import platform

clr.AddReference('System.Net')
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython')

import System.Windows.Forms as WinForms
from IronPython.Hosting import Python

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)

def execute(self, text):
    engine = Python.CreateEngine()

    hosted_sys = Python.GetSysModule(engine)
    hosted_sys.path = sys.path
    hosted_sys.meta_path = sys.meta_path

    result = engine.Execute(text)
    return result

print(platform.platform())

WinForms.MessageBox.Show('Hello', 'Hello from .NET!')