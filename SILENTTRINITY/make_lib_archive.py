from __future__ import print_function
import os
import zipfile

zf = zipfile.ZipFile("Resources/Python.zip", "w")

os.chdir("Resources/Python/")
"""
print(f"[*] Compressing {os.getcwd()}")
for dirname, subdirs, files in os.walk('.'):
    if dirname.find('plumbum') == -1 and dirname.find('rpyc') == -1 and dirname.find("pycache") == -1:
        zf.write(dirname)
        for filename in files:
            zf.write(os.path.join(dirname, filename))

os.chdir("./plumbum/")
print(f"[*] Compressing {os.getcwd()}")
for dirname, subdirs, files in os.walk("plumbum/"):
	if dirname.find("pycache") == -1:
		zf.write(dirname)
		for filename in files:
			zf.write(os.path.join(dirname, filename))

os.chdir("../rpyc/")
print(f"[*] Compressing {os.getcwd()}")
for dirname, subdirs, files in os.walk("rpyc/"):
	if dirname.find("pycache") == -1:
		zf.write(dirname)
		for filename in files:
			zf.write(os.path.join(dirname, filename))
"""

print(f"[*] Compressing {os.getcwd()}")
for dirname, subdirs, files in os.walk('.'):
	zf.write(dirname)
	for filename in files:
	    zf.write(os.path.join(dirname, filename))

zf.close()

print("[*] Done")
