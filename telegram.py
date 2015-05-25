#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM
import re
import json

WEBPAGE_RE = r'(?P<content>.*)\s\[webpage:\s+url:.+\]$'

class LineBuffer(object):
    def __init__(self):
        self.sep = re.compile(r'\r?\n')
        self.buf = b''

    def feed(self, bytes):
        self.buf += bytes

    def lines(self):
        lines = self.sep.split(self.buf)
        self.buf = lines.pop()
        return iter(lines)

    def __iter__(self):
        return self.lines()

class Telegram(object):
    def __init__(self, ip_addr='127.0.0.1', port='4444'):
        self._socket_init(ip_addr, port)
        self.main_session()
        self.msg_re = re.compile(MSG_RE, re.DOTALL)
        self.user_info_re = re.compile(USER_INFO_RE)
        self.content_filter_res = [
            re.compile(WEBPAGE_RE),
        ]
        self.buf = LineBuffer()

    def __del__(self):
        self.sock.close()

    def _socket_init(self, ip_addr, port):
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((ip_addr, port))
        self.sock = s

    def filter_content(self, content):
        for r in self.content_filter_res:
            m = r.match(content)
            if m is not None:
                content = m.group("content")
        return content

    def parse_user_info(self, msg):
        """Parse User Info

        Returns:
            (userId, Username, Realname) if msg is normal
            None if else
        """
        m = self.user_info_re.match(msg)
        return m.groups() if m is not None else None

    def process_recieved(self):
        """Process messages been recieved.

        Returns:
            None
        """
        for m in self.buf:
            try:
                msg = json.loads(m)
            except ValueError:
                pass
            #FIXME: handle msg

    def process_forever(self):
        while True:
            self.buf.feed(self.sock.recv(2 ** 12))
            self.process_recieved()

    def get_user_info(self, user_id):
        cmd = "user_info user#" + user_id
        self.send_cmd(cmd)

    def send_cmd(self, cmd):
        if '\n' != cmd[-1]:
            cmd += '\n'
        self.sock.send(cmd.encode())

    def main_session(self):
        self.send_cmd('main_session')

    def send_msg(self, peer, msg):
        peer = peer.replace(' ', '_')
        cmd = 'msg ' + peer + ' ' + msg
        self.send_cmd(cmd)

    def send_user_msg(self, userid, msg):
        peer = 'user#' + userid
        self.send_msg(peer, msg)

    def send_chat_msg(self, chatid, msg):
        peer = 'chat#' + chatid
        self.send_msg(peer, msg)



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
