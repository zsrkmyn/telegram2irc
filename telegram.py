#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM
import re
import json

class LineBuffer(object):
    def __init__(self):
        self.sep = re.compile(r'\r?\n')
        self.buf = b''

    def feed(self, bytes):
        self.buf += bytes

    def lines(self):
        lines = self.sep.split(self.buf.decode('utf-8'))
        self.buf = lines.pop().encode()
        return iter(lines)

    def __iter__(self):
        return self.lines()

class Telegram(object):
    """A class to connect telegram-cli.

    """

    def __init__(self, ip_addr='127.0.0.1', port='4444'):
        self._socket_init(ip_addr, port)
        self.main_session()
        self.buf = LineBuffer()
        self.event_handlers = {
                'message': None,
                'read': None,
                'update': None,
        }

    def __del__(self):
        self.sock.close()

    def _socket_init(self, ip_addr, port):
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((ip_addr, port))
        self.sock = s

    def register_handler(self, event, handler):
        self.event_handlers[event] = handler

    def remove_handler(self, event):
        self.event_handlers[event] = None

    def process_recieved(self):
        """Process messages been recieved.

        Returns:
            None
        """
        for m in self.buf:
            try:
                msg = json.loads(m)
            except ValueError as e:
                continue

            event = msg.get('event', None)
            if event is not None:
                handler = self.event_handlers.get(event, None)
                if callable(handler):
                    handler(self, msg)

    def process_loop(self):
        while True:
            self.buf.feed(self.sock.recv(2 ** 12))
            self.process_recieved()

    def send_cmd(self, cmd):
        if '\n' != cmd[-1]:
            cmd += '\n'
        self.sock.send(cmd.encode())

    def main_session(self):
        self.send_cmd('main_session')

    def send_msg(self, peer, msg):
        if not (peer.startswith('user#') or peer.startswith('chat#')):
            peer = peer.replace(' ', '_').replace('#', '@')
        cmd = 'msg ' + peer + ' ' + msg
        self.send_cmd(cmd)


if __name__ == '__main__':
    tele = Telegram('127.0.0.1', 1235)
    tele.send_msg('user#67655173', 'hello')
    while True:
        ret = tele.recv_one_msg()
        if ret == -1:
            print('Connect closed')
            break
        else:
            print(ret)
    tele = None
