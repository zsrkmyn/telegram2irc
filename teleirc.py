#!/usr/bin/env python3

import sys
import re
import threading
import pickle
import ssl
import time

import irc.client

from telegram import Telegram
from config import config

def split_message(msg, size):
    b = msg.encode('utf-8')
    if len(b) <= size:
        yield msg
    else:
        prefix = b[:size].decode('utf-8', errors='ignore')
        yield prefix
        yield from split_message(msg[len(prefix):], size)


class BotBase(object):

    help_txt = {
        'all'  : 'current avaliable commands are: .nick, .help, .join, .list',
        'help' : '.help [command] => show help message (for `command`).',
        'nick' : '.nick <new_nick> => change your nick to `new_nick`, no space allowed.',
        'join' : '.join <channel> [channel [channel [...]]] => join `channel`(s). Use `.list` to list avaliable channels.',
        'list' : '.list => list all avaliable chats.',
    }

    msg_format = '[{nick}] {msg}'

    def __init__(self,
            tel_server, tel_port, tel_handlers,
            irc_server, irc_port, irc_nick, irc_usessl,
            irc_blacklist, irc_handlers,
            bindings, usernick_file=None):

        self.tel_connection = None
        self.irc_connection = None
        self.bindings = bindings
        if usernick_file:
            self.load_usernicks(usernick_file)
        else:
            self.load_usernicks()

        self.irc_channels = None

        self.irc_blacklist = []

        self.irc_init(irc_server, irc_port, irc_nick, irc_usessl, irc_handlers)
        self.tel_init(tel_server, tel_port, tel_handlers)

    def main_loop(self):
        def irc_thread():
            def keep_alive_ping(connection):
                try:
                    if time.time() - connection.last_pong > 360:
                        raise irc.client.ServerNotConnectedError('ping timeout!')
                        connection.last_pong = time.time()
                    connection.ping(connection.get_server_name())
                except irc.client.ServerNotConnectedError:
                    print('[irc]  Reconnecting...')
                    connection.reconnect()
                    connection.last_pong = time.time()

            self.irc_reactor.execute_every(60, keep_alive_ping, (self.irc_connection,))
            self.irc_reactor.process_forever(60)

        def tel_thread():
            self.tel_connection.process_loop()

        tasks = []
        for i in (irc_thread, tel_thread):
            t = threading.Thread(target=i, args=())
            t.setDaemon(True)
            t.start()
            tasks.append(t)

        for t in tasks:
            t.join()


    def get_irc_binding(self, tel_chat):
        for binding in self.bindings:
            if binding[1] == tel_chat:
                return binding[0]
        return None

    def get_tel_binding(self, irc_channel):
        for binding in self.bindings:
            if binding[0].lower() == irc_channel.lower():
                return binding[1]
        return None

    def get_usernick(self, peer):
        return self.usernicks.get(peer, None)

    def change_usernick(self, peer, newnick):
        self.usernicks[peer] = newnick
        self.save_usernicks()

    def send_help(self, peer, help='all'):
        try:
            m = self.help_txt[help]
        except KeyError:
            m = self.help_txt['all']

        self.tel_connection.send_msg(peer, m)

    def invite_to_join(self, peer, chatlist):
        for c in chatlist:
            chat = self.get_tel_binding(c)

            if chat is not None:
                cmd = 'chat_add_user {chat} {user}'.format(
                    chat=chat.replace(' ', '_').replace('#', '@'),
                    user=peer,
                )
                self.tel_connection.send_cmd(cmd)
            else:
                self.tel_connection.send_msg(peer,
                        '{0} is not avaliable. Use `.list` to see avaliable channels'.format(c))

    def handle_command(self, content, peer):
        if not content.startswith('.'):
            return

        try:
            tmp = content.split()
            cmd = tmp[0][1:].lower()
            args = tmp[1:]
        except IndexError:
            self.send_help(peer)

        if cmd == 'nick':
            try:
                self.change_usernick(peer, args[0])
                self.tel_connection.send_msg(peer, 'Your nick has changed to {0}'.format(args[0]))
            except IndexError:
                self.send_help(peer, 'nick')
        elif cmd == 'help':
            try:
                self.send_help(peer, args[0])
            except IndexError:
                self.send_help(peer, 'help')
                self.send_help(peer)
        elif cmd == 'join':
            if len(args) == 0:
                self.send_help(peer, 'join')
            self.invite_to_join(peer, args)
        elif cmd == 'list':
            channels = ', '.join([c for c, h in self.irc_channels if h == 0])
            self.tel_connection.send_msg(peer, channels)
        else:
            self.send_help(peer)

    def irc_init(self, server, port, nickname, usessl, handlers):
        self.irc_channels = [(c, h) for c, *_, h in self.bindings]

        # use a replacement character for unrecognized byte sequences
        # see <https://pypi.python.org/pypi/irc>
        irc.client.ServerConnection.buffer_class.errors = 'replace'
        reactor = irc.client.Reactor()
        irc_connection = reactor.server()

        try:
            if usessl:
                ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
                irc_connection.connect(server, port, nickname,
                        connect_factory=ssl_factory)
            else:
                irc_connection.connect(server, port, nickname)
        except irc.client.ServerConnectionError:
            print(sys.exc_info()[1])

        for event, handler in handlers.items():
            irc_connection.add_global_handler(event, handler)

        irc_connection.last_pong = time.time()

        self.irc_connection = irc_connection
        self.irc_reactor = reactor

    def tel_init(self, server, port, handlers):
        connection = Telegram(server, port)
        for event, handler in handlers.items():
            connection.register_handler(event, handler)

        self.tel_connection = connection

    def load_usernicks(self, filename='usernicks'):
        try:
            with open(filename, 'rb') as f:
                self.usernicks = pickle.load(f)
        except Exception as e:
            print(e)
            self.usernicks = {}

    def save_usernicks(self, filename='usernicks'):
        try:
            with open(filename, 'wb') as f:
                pickle.dump(self.usernicks, f, pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass


class MainBot(BotBase):
    def __init__(self, *args, **kwargs):
        irc_handlers = {
                "welcome": self.irc_on_connect,
                "join": self.irc_on_join,
                "privmsg": self.irc_on_privmsg,
                "pubmsg": self.irc_on_privmsg,
                "action": self.irc_on_privmsg,
                "pong": self.irc_on_pong,
                "nicknameinuse": self.irc_on_nickinuse,
        }
        tel_handlers = {
                "message": self.tel_on_message,
        }
        super().__init__(*args,
                irc_handlers=irc_handlers,
                tel_handlers=tel_handlers,
                **kwargs)

    def _handler(func):
        def wrapper(self, *arg, **kwargs):
            func(self, *arg, **kwargs)
        return wrapper

    @_handler
    def irc_on_pong(self, connection, event):
        connection.last_pong = time.time()
        print('[irc]  PONG from: ', event.source)

    @_handler
    def irc_on_connect(self, connection, event):
        for (channel, *_) in self.irc_channels:
            if irc.client.is_channel(channel):
                connection.join(channel)

    @_handler
    def irc_on_join(self, connection, event):
        print('[irc] ', event.source + ' ' + event.target)

    @_handler
    def irc_on_privmsg(self, connection, event):
        print('[irc] ', event.source + ' ' + event.target + ' ' + event.arguments[0])

        tel_target = self.get_tel_binding(event.target)
        irc_nick = event.source[:event.source.index('!')]
        msg = event.arguments[0]

        if tel_target is not None and irc_nick not in self.irc_blacklist:
            self.tel_connection.send_msg(
                    tel_target,
                    self.msg_format.format(
                        nick = irc_nick,
                        msg = msg
                    )
            )

    @_handler
    def irc_on_nickinuse(self, connection, event):
        connection.nick(connection.get_nickname() + '_')

    @_handler
    def tel_on_message(self, connection, message):
        try:
            from_peer = message['from']['print_name']
            from_peer_id = message['from']['id'].__str__()
            from_type = message['from']['type']
            to_peer = message['to']['print_name']
            to_peer_id = message['to']['id'].__str__()
            to_type = message['to']['type']
            is_out = message['out']
            content = message['text']  # delete this line if need handle image
        except KeyError:
            return

        #content = message.get('text', None) or message.get('media', None)

        if is_out:
            return

        print('[tel] ', from_peer, to_peer, content)
        if to_type == 'chat':         # msg is from a chat and need to forward to irc
            to_peer_title = message['to']['title']
            irc_target = self.get_irc_binding('chat#'+to_peer_id) or \
                    self.get_irc_binding(to_peer_title)
        elif content.startswith('.'): # msg is from user and is a command
            self.handle_command(content, from_peer)
            return
        else:                         # msg is from user and user needs help
            self.send_help(from_peer)
            return

        if irc_target is not None:
            nick = self.get_usernick(from_peer) or \
                    self.get_usernick(from_peer_id) or \
                    from_peer.replace(' ', '_')

            lines = content.split('\n')
            for line in lines:
                for seg in split_message(line, 300):
                    self.irc_connection.privmsg(irc_target,
                            self.msg_format.format(nick=nick, msg=seg))
                    time.sleep(1)

def main():
    init_args = {
        'tel_server': config['telegram']['server'],
        'tel_port': config['telegram']['port'],
        'irc_blacklist': config['irc']['blacklist'],
        'irc_server': config['irc']['server'],
        'irc_port': config['irc']['port'],
        'irc_nick': config['irc']['nick'],
        'irc_usessl': config['irc']['ssl'],
        'bindings': config['bindings'],
    }

    bot = MainBot(**init_args)
    try:
        bot.main_loop()
    except (Exception, KeyboardInterrupt):
        try:
            bot.irc_connection.quit('Bye')
            bot.irc_connection = None
            bot.tel_connection = None
        except Exception:
            pass
    finally:
        print('Bye.')

if __name__ == '__main__':
    main()
