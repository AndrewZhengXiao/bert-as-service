#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Han Xiao <artex.xh@gmail.com> <https://hanxiao.github.io>

import sys
import uuid

import numpy as np
import zmq
from zmq.utils import jsonapi

if sys.version_info >= (3, 0):
    _str = str
    _buffer = memoryview
    _unicode = lambda x: x
else:
    # make it compatible for py2
    _str = basestring
    _buffer = buffer
    _unicode = lambda x: [BertClient.force_to_unicode(y) for y in x]


class BertClient:
    def __init__(self, ip='localhost', port=5555, port_out=5556, output_fmt='ndarray', show_server_config=False):
        self.context = zmq.Context()
        self.sender = self.context.socket(zmq.PUSH)
        self.identity = str(uuid.uuid4()).encode('ascii')
        self.sender.connect('tcp://%s:%d' % (ip, port))
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.setsockopt(zmq.SUBSCRIBE, self.identity)
        self.receiver.connect('tcp://%s:%d' % (ip, port_out))
        self.ip = ip
        self.port = port

        if output_fmt == 'ndarray':
            self.formatter = lambda x: x
        elif output_fmt == 'list':
            self.formatter = lambda x: x.tolist()
        else:
            raise AttributeError('"output_fmt" must be "ndarray" or "list"')

        if show_server_config:
            self.get_server_config()
            print('you should NOT see this message multiple times! '
                  'if you see it appears repeatedly, '
                  'consider moving "BertClient()" out of the loop.')

    def send(self, msg):
        self.sender.send_multipart([self.identity, msg])

    def get_server_config(self):
        self.send(b'SHOW_CONFIG')
        response = self.sender.recv_multipart()
        print('connect success!\nserver at %s:%d returns the following config:' % (self.ip, self.port))
        for k, v in jsonapi.loads(response[0]).items():
            print('%30s\t=\t%-30s' % (k, v))

    def encode(self, texts):
        texts = _unicode(texts)
        if self.is_valid_input(texts):
            self.send(jsonapi.dumps(texts))
            response = self.receiver.recv_multipart()
            arr_info, arr_val = jsonapi.loads(response[1]), response[2]
            X = np.frombuffer(_buffer(arr_val), dtype=arr_info['dtype'])
            return self.formatter(X.reshape(arr_info['shape']))
        else:
            raise AttributeError('"texts" must be "List[str]" and non-empty!')

    @staticmethod
    def is_valid_input(texts):
        return isinstance(texts, list) and all(isinstance(s, _str) and s.strip() for s in texts)

    @staticmethod
    def force_to_unicode(text):
        "If text is unicode, it is returned as is. If it's str, convert it to Unicode using UTF-8 encoding"
        return text if isinstance(text, unicode) else text.decode('utf-8')
