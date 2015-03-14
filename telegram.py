#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM
import re

MSG_RE = r'\[(\d{2}:\d{2})\]\s+(chat#(\d+))?\s+user#(\d+)\s+>>>\s+(.*)'

class Telegram(object):
    def __init__(self, ip_addr='127.0.0.1', port='4444'):
        self._socket_init(ip_addr, port)
        self.main_session()
        self.msg_re = re.compile(MSG_RE)
        self.buf = ''

    def __destory__(self):
        self.sock.close()

    def _socket_init(self, ip_addr, port):
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((ip_addr, port))
        self.sock = s

    def send_cmd(self, cmd):
        if '\n' != cmd[-1]:
            cmd += '\n'
        self.sock.send(cmd.encode())

    def main_session(self):
        self.send_cmd('main_session')

    def send_msg(self, peer, msg):
        peer = peer.replace(' ', '_')
        cmd = 'msg ' + peer + ' ' + msg;
        self.send_cmd(cmd)

    def parse_msg(self, msg):
        """Parse message.

        Retuns:
            (time, chatID, userID, content) if 'msg' is normal.
            None if else.
        """
        m = self.msg_re.match(msg)
        if m is not None:
            g = m.groups()
            return g[:1] + g[2:]
        else:
            return None

    def recv_one_msg(self):
        """Receive one message.

        Returns:
            None if needs to receive more or is not a message.
            -1 if connection is closed.
            (time, chatID, userID, content) if normal.
        """
        try:
            pos = self.buf.index('\n')
        except ValueError:
            ret = self.sock.recv(4096)

            if '' == ret:
                return None

            try:
                self.buf += ret.decode('utf-8')
            except UnicodeDecodeError:
                self.buf = ''

        try:
            pos = self.buf.index('\n')
        except ValueError:
            # needs to recv more.
            return -1

        line = self.buf[:pos]
        self.buf = self.buf[pos + 1:]

        msg = self.parse_msg(line)

        try:
            if msg[1] is not None:
                target = 'chat#' + msg[1]
            else:
                target = 'user#' + msg[2]
            self.send_cmd('mark_read ' + target)
        except TypeError:
            # msg is None
            pass

        return msg

if __name__ == '__main__':
    tele = Telegram('127.0.0.1', 1235)
    tele.send_msg('user#67655173', 'hello')
    while True:
        ret = tele.recv_one_msg()
        if ret == -1:
            print('Connect closed')
            break
        elif ret is None:
            print('No a user message or needs to recieve more')
        else:
            print(ret)
    tele = None
