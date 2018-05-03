from __future__ import unicode_literals, print_function
import eventlet
import logging

eventlet.monkey_patch()

logging.basicConfig(format="%(asctime)s [%(levelname)s] - %(filename)s: %(funcName)s - %(message)s", level=logging.DEBUG)
