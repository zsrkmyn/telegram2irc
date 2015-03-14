#! /usr/bin/env python3

import sys
import argparse
import itertools
import threading

import irc.client

from telegram import Telegram
from config import config

tele = None
irc_c = None
bindings = tuple()

irc_channels = []
tele_me = None

def on_connect(connection, event):
    for c in irc_channels:
        if irc.client.is_channel(c):
            connection.join(c)

def on_join(connection, event):
    print(event.source + ' ' + event.target)

def on_privmsg(connection, event):
    print(event.source + ' ' + event.target + ' ' + event.arguments[0])
    tele_chat = get_tele_binding(event.target)
    if tele_chat is not None:
        tele.send_msg(tele_chat, '[' + event.source[:event.source.index('!')] +
                                 ']: ' + event.arguments[0])

def on_nickinuse(connection, event):
    connection.nick(connection.get_nickname() + '_')

def get_lines():
    while True:
        yield sys.stdin.readline().strip()

def main_loop():
    while True:
        ret = tele.recv_one_msg()
        if ret == -1:
            break

        elif ret is not None and ret[2] != tele_me:
            if ret[1] is not None:
                irc_target = get_irc_binding('chat#'+ret[1])
            else:
                irc_target = get_irc_binding('user#'+ret[2])

            if irc_target is not None:
                irc_c.privmsg(irc_target, '['+ret[2]+']: '+ret[3])

    connection.quit("Bye")

def on_disconnect(connection, event):
    raise SystemExit()

def get_irc_binding(tele_chat):
    for b in bindings:
        if b[1] == tele_chat:
            return b[0]
    return None

def get_tele_binding(irc_chan):
    for b in bindings:
        if b[0] == irc_chan:
            return b[1]
    return None

def irc_init():
    global irc_channels
    global irc_c

    irc_channels = [i[0] for i in config['bindings']]
    server = config['irc']['server']
    port = config['irc']['port']
    nickname = config['irc']['nick']

    reactor = irc.client.Reactor()
    try:
        irc_c = reactor.server().connect(server, port, nickname)
    except irc.client.ServerConnectionError:
        print(sys.exc_info()[1])
        raise SystemExit(1)

    irc_c.add_global_handler("welcome", on_connect)
    irc_c.add_global_handler("join", on_join)
    irc_c.add_global_handler("privmsg", on_privmsg)
    irc_c.add_global_handler("pubmsg", on_privmsg)
    irc_c.add_global_handler("disconnect", on_disconnect)
    irc_c.add_global_handler("nicknameinuse", on_nickinuse)

    threading.Thread(target=reactor.process_forever, args=(None,)).start()

def main():
    global tele
    global bindings
    global tele_me

    bindings = config['bindings']

    irc_init()

    tele_me = config['telegram']['me'].replace('user#', '')
    tele = Telegram('127.0.0.1', 1235)
    main_loop()

if __name__ == '__main__':
    main()
