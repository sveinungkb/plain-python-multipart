# Copyright 2024 Sveinung Kval Bakken
# Free for all use in any form.
# https://github.com/sveinungkb/plain-python-multipart

import socket
import time
from multipart import Request

HOST = "127.0.0.1"
PORT = 65432

def log(msg):
    print('%.3f [www] %s' % (time.monotonic(), msg))

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.settimeout(1.0)
    s.setblocking(True)
    s.listen()
    log('listening to %s:%s' % (HOST, PORT))
    while True:
        conn, addr = s.accept()
        with conn:
            log(f"connected by {addr}")
            start = time.monotonic()
            request = Request()
            response = None
            while True:
                log('receive start')
                try:
                    data = conn.recv(2048)
                    log('receive done %d' % len(data) if data else -1)
                    if data:
                        response = request.onData(data)
                    log('got response? %s' % response)
                    if response:
                        log('sending response after %.3fs' % (time.monotonic() - start))
                        conn.sendall(response)
                        log('closing')
                        conn.close()
                        break
                except ConnectionError as e:
                    log('Socket exception: %s' % e)
    s.close()
