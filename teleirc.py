#! /usr/bin/env python3

import sys
import argparse
import itertools
import threading
import pickle
import ssl

import irc.client

from telegram import Telegram
from config import config

help_txt = {
    'all'  : 'current avaliable commands are: nick, help, join, list',
    'help' : 'help [command] => show help message (for `command`).',
    'nick' : 'nick <new_nick> => change your nick to `new_nick`, no space allowed.',
    'join' : 'join <channel> [channel [channel [...]]] => join `channel`s. use `list` to list channel.',
    'list' : 'list => list all avaliable chats.',
}

msg_format = '[{nick}] {msg}'

tele_conn = None
irc_conn = None
bindings = tuple()
usernicks = {}

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
    tele_target = get_tele_binding(event.target)
    if tele_target is not None:
        tele_conn.send_msg(
                tele_target,
                msg_format.format(
                    nick=event.source[:event.source.index('!')],
                    msg = event.arguments[0]
                )
        )

def on_nickinuse(connection, event):
    connection.nick(connection.get_nickname() + '_')

def on_disconnect(connection, event):
    raise SystemExit()

def main_loop():
    while True:
        msg = tele_conn.recv_one_msg()
        if msg == -1:
            break

        elif msg is not None and msg[2] != tele_me:
            if msg[1] is not None:
                # msg is from chat group
                irc_target = get_irc_binding('chat#'+msg[1])
            elif msg[3].startswith('.'):
                # msg is from user and is a command
                handle_command(msg)
                irc_target = None
            else:
                # msg is from user and is not a command
                irc_target = get_irc_binding('user#'+msg[2])


            if irc_target is not None:
                nick = get_usernick_from_id(msg[2])
                if nick is None:
                    nick = msg[2]
                irc_conn.privmsg(irc_target, msg_format.format(nick=nick, msg=msg[3]))

    irc_conn.quit("Bye")
    exit(0)

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

def get_usernick_from_id(userid):
    try:
        nick = usernicks[userid]
    except KeyError:
        nick = None

    return nick

def change_usernick(userid, newnick):
    usernicks[userid] = newnick
    save_usernicks()

def send_help(userid, help='all'):
    try:
        m = help_txt[help]
    except KeyError:
        m = help_txt['all']

    tele_conn.send_user_msg(userid, m)

def invite_to_join(userid, chatlist):
    for c in chatlist:
        chat = get_tele_binding(c)

        if chat is not None:
            cmd = 'chat_add_user {chat} {user} 0'.format(
                    chat = chat,
                    user = 'user#' + userid
                    )
            tele_conn.send_cmd(cmd)
        else:
            tele_conn.send_user_msg(userid, '{0} is not avaliable. Use `.list` to see avaliable channels'.format(c))

def handle_command(msg):
    if not msg[3].startswith('.'):
        return

    userid = msg[2]
    try:
        tmp = msg[3].split()
        cmd = tmp[0][1:].lower()
        args = tmp[1:]
    except IndexError:
        send_help(userid)

    if cmd == 'nick':
        try:
            change_usernick(userid, args[0])
            tele_conn.send_user_msg(userid, 'Your nick has changed to {0}'.format(args[0]))
        except IndexError:
            send_help(userid, 'nick')
    elif cmd == 'help':
        try:
            send_help(userid, args[0])
        except IndexError:
            send_help(userid, 'help')
        send_help(userid)
    elif cmd == 'join':
        if len(args) == 0:
            send_help(userid, 'join')
        invite_to_join(userid, args)
    elif cmd == 'list':
        chan = ', '.join([i[0] for i in bindings])
        tele_conn.send_user_msg(userid, chan)
    else:
        send_help(userid)

def irc_init():
    global irc_channels
    global irc_conn

    irc_channels = [i[0] for i in config['bindings']]
    server = config['irc']['server']
    port = config['irc']['port']
    nickname = config['irc']['nick']
    usessl = config['irc']['ssl']

    # use a replacement character for unrecognized byte sequences
    # see <https://pypi.python.org/pypi/irc>
    irc.client.ServerConnection.buffer_class.errors = 'replace'

    reactor = irc.client.Reactor()

    if usessl:
        ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)

    try:
        if usessl:
            irc_conn = reactor.server().connect(server, port, nickname,
                                                connect_factory=ssl_factory)
        else:
            irc_conn = reactor.server().connect(server, port, nickname)
    except irc.client.ServerConnectionError:
        print(sys.exc_info()[1])

    irc_conn.add_global_handler("welcome", on_connect)
    irc_conn.add_global_handler("join", on_join)
    irc_conn.add_global_handler("privmsg", on_privmsg)
    irc_conn.add_global_handler("pubmsg", on_privmsg)
    irc_conn.add_global_handler("action", on_privmsg)
    irc_conn.add_global_handler("disconnect", on_disconnect)
    irc_conn.add_global_handler("nicknameinuse", on_nickinuse)

    threading.Thread(target=reactor.process_forever, args=(None,)).start()

def tele_init():
    global tele_conn
    global tele_me

    server = config['telegram']['server']
    port = config['telegram']['port']
    tele_me = config['telegram']['me'].replace('user#', '')
    tele_conn = Telegram(server, port)

def load_usernicks():
    global usernicks
    try:
        with open('usernicks', 'rb') as f:
            usernicks = pickle.load(f)
    except Exception:
        usernicks = {}

def save_usernicks():
    global usernicks
    try:
        with open('usernicks', 'wb') as f:
            pickle.dump(usernicks, f, pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass

def main():
    global bindings
    bindings = config['bindings']
    load_usernicks()

    irc_init()
    tele_init()

    main_loop()

if __name__ == '__main__':
    main()
