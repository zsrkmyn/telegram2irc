Description
===========
This is a bot who can connect IRC channels with Telegram chat groups.

Dependencies
==========
+ `python-irc <https://pypi.python.org/pypi/irc>`_
+ `tg <https://github.com/vysheng/tg>`_

Usage
=====
#. If you have not used telegram-cli before, run it first, and set the correct phone number
   to log in.

#. Create chat groups using ``create_group_chat`` command in ``telegram-cli``, and use
   ``dialog_list`` to check wheather the groups are created successfully. Then exit the
   client.

#. Rename the ``config.py.example`` to ``config.py`` and edit it.

   #. Set ``bindings`` to bind IRC channels with Telegram chats. Elements in ``binddings`` tuple
      are tuples with three element, whose first element is IRC channel and the second one is
      Telegram chat (both chat ID and chat name are acceptable) and the third element is either ``0``
      or ``1``, if ``1`` is set, the channel will *not* be listed in ``.list`` command (See ``.help``).
   #. ``blacklist`` in ``irc`` is a list which contains some nicks in IRC. The messages of these
      nicks won't be forwarded to Telegram.

#. Start the ``telegram-cli`` using ``telegram-cli --json -d -P <port>``, where ``<port>`` is the telegram
   client port you filled in ``config.py`` file, and ``-I`` is mandatory, ``-d`` is optional.

#. Start the bot using ``python3 teleirc.py``, then it will join the channels automatically and
   forwards the messages between Telegram and IRC.

#. Add the bot as a contact on other Telegram accounts, and send ``.help`` to it, you can get the
   information about how to join a chat group, how to change the nick and etc.

TODO
====
#. Split IRC message if it is too long.

#. Add restarting function.

#. Write comment for the code.

#. Use logger instead of print.

License
=======
This software is released with MIT License. See ``LICENSE`` file for more details.
