#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM
import re

MSG_RE = r'ANSWER\s+\d+\n\[(\d{2}:\d{2})\]\s+(chat#(\d+))?\s+user#(\d+)\s+>>>\s+(.*)'
USER_INFO_RE = (
    r"ANSWER\s+\d+\n"
    r'User\s+user#(\d+)\s+@([a-zA-Z0-9_\-]*)\s+\(#\d+\):\n'
    r"\s+real\s+name:\s(.+)\n.*"
)
WEBPAGE_RE = r'(?P<content>.*)\s\[webpage:\s+url:.+\]$'


class Telegram(object):
    def __init__(self, ip_addr='127.0.0.1', port='4444'):
        self._socket_init(ip_addr, port)
        self.main_session()
        self.msg_re = re.compile(MSG_RE, re.DOTALL)
        self.user_info_re = re.compile(USER_INFO_RE)
        self.content_filter_res = [
            re.compile(WEBPAGE_RE),
        ]
        self.buf = ''

    def __del__(self):
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
        cmd = 'msg ' + peer + ' ' + msg
        self.send_cmd(cmd)

    def send_user_msg(self, userid, msg):
        peer = 'user#' + userid
        self.send_msg(peer, msg)

    def send_chat_msg(self, chatid, msg):
        peer = 'chat#' + chatid
        self.send_msg(peer, msg)

    def filter_content(self, content):
        for r in self.content_filter_res:
            m = r.match(content)
            if m is not None:
                content = m.group("content")
        return content

    def parse_msg(self, msg):
        """Parse message.

        Returns:
            (time, chatID, userID, content) if 'msg' is normal.
            None if else.
        """
        m = self.msg_re.match(msg)
        if m is not None:
            g = m.groups()
            content = self.filter_content(g[-1])
            return (g[0], g[2], g[3], content)
        else:
            return None

    def parse_user_info(self, msg):
        """Parse User Info

        Returns:
            (userId, Username, Realname) if msg is normal
            None if else
        """
        m = self.user_info_re.match(msg)
        return m.groups() if m is not None else None

    def recv_one_msg(self):
        """Receive one message.

        Returns:
            -1 if connection is closed.
            (time, chatID, userID, content) if normal.
        """
        while True:
            ret = self.sock.recv(4096)

            if '' == ret:
                return -1

            try:
                self.buf += ret.decode('utf-8')
            except UnicodeDecodeError:
                self.buf = ''

            while True:
                try:
                    pos = self.buf.index('\n\n')
                except ValueError:
                    # needs to recv more.
                    break

                line = self.buf[:pos]
                self.buf = self.buf[pos + 2:]

                msg = self.parse_msg(line)
                if msg is not None:
                    if msg[1] is not None:
                        target = 'chat#' + msg[1]
                    else:
                        target = 'user#' + msg[2]
                    self.send_cmd('mark_read ' + target)
                    return msg

                info = self.parse_user_info(line)
                if info is not None:
                    return info

    def get_user_info(self, user_id):
        cmd = "user_info user#" + user_id
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
