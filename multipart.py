# Copyright 2024 Sveinung Kval Bakken
# Free for all use in any form.
# https://github.com/sveinungkb/plain-python-multipart

import time

_MAX_BUFFER = 2048
_INDEX_HTML = """
<html>
    <head><title>plain-python-multipart file upload</title></head>
    <body>
        <form action="/" enctype="multipart/form-data" method="post">
            <input type="file" name="files" multiple>
            <input type="submit"/>
        </form>
    </body>
</html>
"""

def log(msg):
    print('%.3f [www] %s' % (time.monotonic(), msg))

def bytes_to_hex_string(data: bytes, offset: int = 0):
    if len(data) < 20:
        return ' '.join(hex(b) for b in data)
    return ' '.join(hex(b) for b in data[offset:offset + 10]) + '..' + ' '.join(hex(b) for b in data[-10:])

class RequestHead(object):
    def __init__(self, data) -> None:
        lines = data.decode('utf-8').split('\r\n')
        self.method, self.path, self.protocol = lines[0].split(' ')
        self.headers = []
        for line in lines[1:]:
            self.headers.append(line.split(': '))
        log('got request %s %s %s, headers: %s' % (self.method, self.path, self.protocol, self.headers))

    def header(self, name: str) -> str:
        for k, v in self.headers:
            if name == k:
                return v
        return None

class FilePart(object):
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.headers = None
        self.file = None

    def headerKey(self, name: str) -> str:
        for header in self.headers:
            headerStart = header.find(name)
            if headerStart >= 0:
                valueStart = header.find('"', headerStart) + 1
                valueEnd = header.find('"', valueStart)
                return header[valueStart:valueEnd]
        return None

    def onData(self, data: bytes):
        log('part %s ondata %d bytes buffered: %s' % (self, len(self.buffer), bytes_to_hex_string(data)))
        if len(self.buffer) > _MAX_BUFFER:
            raise Exception('Part buffer greater than limit %d/%d' % (len(self.buffer), _MAX_BUFFER))
        if self.file:
            with open(self.file, 'ab') as file:
                file.write(data)

        if not self.headers:
            self.buffer.extend(data)
            partHeadersEnd = self.buffer.find(b'\r\n\r\n')
            if partHeadersEnd >= 0:
                self.headers = self.buffer[0:partHeadersEnd].decode('utf-8').split('\r\n')
                self.file = self.headerKey('filename') + '.out'
                with open(self.file, 'wb') as file:  # creates new file
                    file.write(self.buffer[partHeadersEnd + 4:])

    def close(self):
        log('part %s close %d bytes: %s' % (self, len(self.buffer), bytes_to_hex_string(self.buffer)))

    def __str__(self) -> str:
        return 'FilePart %s' % self.file

class MultiPartReader(object):
    def __init__(self, contentType: str) -> None:
        contentType, boundary = contentType.split('; boundary=')
        log('multi part reader for boundary: %s' % boundary)
        self.boundaryStart = ('--%s\r\n' % boundary).encode('utf-8')
        self.boundaryEnd = ('--%s--\r\n' % boundary).encode('utf-8')
        self.buffer = bytearray()
        self.part = None

    def onData(self, data: bytes):
        log('ondata body part reader [%s]' % bytes_to_hex_string(data))
        self.buffer.extend(data)
        # log('buffer: %s' % self.buffer.decode('utf-8'))
        partStart = self.buffer.find(self.boundaryStart)
        partEnd = self.buffer.find(self.boundaryEnd)
        if partStart >= 0:
            log('found part start at %d' % partStart)
            if self.part:
                log('delivering rest of old part 0:%d' % partStart)
                self.part.onData(self.buffer[0:partStart - 2])  # Remove trailing \r\n
                self.part.close()
            self.part = FilePart()
            self.buffer = self.buffer[partStart + len(self.boundaryStart):]
            # log('moved buffer to: %s' % self.buffer.decode('utf-8'))
            # Recursive call to look for more boundaries and pass data from existing buffer
            self.onData([])
        elif partEnd >= 0:
            log('found parts end at %d' % partEnd)
            if self.part:
                self.part.onData(self.buffer[0:partEnd - 2])
                self.part.close()
                self.part = None
                self.buffer = self.buffer[partEnd + len(self.boundaryEnd):]
        elif self.part:
            if len(self.buffer) > 128:
                # Leave 128 bytes in buffer, in case we have a partial boundary
                log('deliver %d/%d bytes' % (len(self.buffer) - 128, len(self.buffer)))
                self.part.onData(self.buffer[0:len(self.buffer) - 128])
                self.buffer = self.buffer[len(self.buffer) - 128:]
                self.onData([])
            else:
                log('deliver %d/%s bytes' % (len(self.buffer), len(self.buffer)))
                self.part.onData(self.buffer)
                self.buffer = bytearray()
        if len(self.buffer) > _MAX_BUFFER:
            raise Exception('Part reader buffer greater than limit %d/%d' % (len(self.buffer), _MAX_BUFFER))


class Request(object):
    """
    Main request processing class, feed it request data with onData.
    The head  of the request and the multipart body is read with a buffer, each part is streamed without further buffering after
    part headers are processed.

    Implement your own version of FilePart to handle where data is written, this is only intended as an example and for testing
    and will write files to its filename + .out.

    Methods
    -------
    onData(data:bytes) -> bytes
        Process data as part of request, class will return None until request is fully processed and a response is ready.
    """

    def __init__(self) -> None:
        self.buffer = bytes()
        self.head = None
        self.body = None
        self.position = 0

    def onData(self, data: bytes) -> bytes:
        log('request onData %d bytes' % len(data))
        if not self.head:
            self.buffer += data
            headEnd = self.buffer.find(b'\r\n\r\n')
            if headEnd > 0:
                self.head = RequestHead(self.buffer[0:headEnd])
                log('head end found at %d' % headEnd)
                if 'POST' == self.head.method:
                    contentType = self.head.header('Content-Type')
                    if 'multipart/form-data' in contentType:
                        self.body = MultiPartReader(contentType)
                        bufferedBody = self.buffer[headEnd + 4:]
                        log('deliver buffer to body %s' % bytes_to_hex_string(bufferedBody))
                        self.buffer = None  # no longer needed now
                        return self.onData(bufferedBody)
                    else:
                        return ("HTTP/1.0 400 Bad Request\r\nConnection: close\r\n\r\n<html>Content-Type not supported: %s</html>\r\n" % contentType).encode('utf-8')
                elif 'GET' == self.head.method and '/' == self.head.path:
                    return ("HTTP/1.0 200 OK\r\nConnection: close\r\n\r\n%s\r\n" % _INDEX_HTML).encode('utf-8')
                elif 'OPTIONS' and '/' == self.head.path:
                    return b"HTTP/1.0 200 OK\r\nConnection: close\r\nContent-Type: text/html\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: content-type\r\n\r\n"
                else:
                    return ("HTTP/1.0 400 Bad Request\r\nConnection: close\r\n\r\n<html>Not found: %s</html>\r\n" % self.head.path).encode('utf-8')
        elif self.body:
            self.position += len(data)
            log('request ondata body')
            contentLength = int(self.head.header('Content-Length'))
            log('ondata %d bytes %d/%d (%.2f) of body' % (
            len(data), self.position, contentLength, self.position / contentLength))
            self.body.onData(data)
            if self.position == contentLength:
                log('body fully read, return response')
                return b"HTTP/1.0 200 OK\r\nConnection: close\r\n\r\n<html>Upload OK %d/%d bytes</html>\r\n" % (
                self.position, contentLength)
        return None
