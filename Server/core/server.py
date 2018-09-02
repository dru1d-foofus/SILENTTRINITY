import ssl
#import asyncio
#from time import sleep
#from multiprocessing import Process
from pprint import pprint
import json
from quart import Quart, websocket, request, jsonify

app = Quart(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
async def handler(path):
    print(f"Path: {path}")
    print(request.headers)
    if request.method == 'GET':
        if path == 'stage.zip':
            #print(f"Staging {request.})
    if request.method == 'POST':
        data = json.loads(await request.data)
        pprint(data)

    resp = jsonify({})
    resp.status_code = 200
    return resp

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
    ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
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
