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

#. Run ``telegram-cli -I``. ``-I`` is needed to make the client use IDs instead of names.
   Run ``dialog_list`` to get chat group IDs and run ``contact_list`` to get your IDs. Then
   exit the client.

#. Edit the ``config.py`` file.

   #. Set the ``me`` to your IDs to avoid the bot sending duplicated message.
   #. Set ``bindings`` to bind IRC channels with Telegram chats. Elements in ``binddings`` tuple
      are tuples, whose first element is IRC channel and the second element is Telegram chat ID.
   #. ``blacklist`` in ``irc`` is a list which contains some nicks in IRC. The messages of these
      nicks won't be forwarded to Telegram.

#. Start the ``telegram-cli`` using ``telegram -I -d -P <port>``, where ``<port>`` is the telegram
   client port you filled in ``config.py`` file, and ``-I`` is needed, ``-d`` is optional.

#. Start the bot using ``python3 teleirc.py``, then it will join the channels automatically and
   forwards the messages between Telegram and IRC.

#. Add the bot as a contact on other Telegram accounts, and send ``.help`` to it, you can get the
   information about how to join a chat group, how to change the nick and etc.

TODO
====

License
=======
This software is released with MIT License. See ``LICENSE`` file for more details.
