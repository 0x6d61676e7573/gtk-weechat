# gtk-weechat
GTK3 client for [WeeChat](https://weechat.org), based on [QWeeChat](https://github.com/weechat/qweechat), written by Sébastien Helleu and released under the terms of the GPL3 license.

## Getting Started

### Prerequisits
These are needed to run gtk-weechat:
- Python>=3.0,
- PyGObject

Instructions for installing the dependencies are available [here](https://pygobject.readthedocs.io/en/latest/getting_started.html) (skip the first paragraph and jump directly to the install instructions for your OS). In some cases, they are already installed by default.

You also need a running WeeChat session to connect to. When you have installed WeeChat, you need to enable the WeeChat relay protocol by executing theses commands in WeeChat (pick your own password and port number)
```
/set relay.network.password "mypassword"
/relay add ssl.weechat 9001
```
You need to create a SSL certificate and private key, by executing these commands on your server terminal.
```
mkdir -p ~/.weechat/ssl
cd ~/.weechat/ssl
openssl req -nodes -newkey rsa:2048 -keyout relay.pem -x509 -days 365 -out relay.pem
```
Then, either restart WeeChat or run this command
```
/relay sslcertkey
```

You can also set up an unencrypted connection, which is simpler but dangerous. For details, see the [WeeChat documentation](https://weechat.org/files/doc/stable/weechat_user.en.html#relay_plugin). Remember that by default, WeeChat enables the user to run arbitrary code on the machine it is running on.

### Installing
You only have to clone the repository in order to run gtk-weechat. Type the following into your terminal and execute the command.
```
git clone https://github.com/0x6d61676e7573/gtk-weechat.git
```

### Running
In order to run gtk-weechat, open a terminal and execute these commands.
```
cd gtk-weechat
python3 gtk-weechat.py
```

Configuration is stored in `$XDG_CONFIG_HOME/gtk-weechat/gtk-weechat.conf`, or the local source directory.

Styles can be loaded from, in order of precedence, `XDG_DATA_HOME/gtk-weechat/css/`, `$XDG_DATA_DIRS/gtk-weechat/css/` or the local source directory

## Contributing
Bug reports are greatly appreciated.

## TODO:
- [ ] Application icon.

## License

This project is licensed under GNU General Public License v3.0.
