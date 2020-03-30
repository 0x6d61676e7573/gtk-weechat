# gtk-weechat
GTK3 client for WeeChat, ported from qweechat.

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

## Contributing
Bug reports are greatly appreciated.

## TODO:
High priority:
- [x] Make hyperlinks clickable.
- [x] Add a way to use dark color scheme without changing system color scheme
- [x] Make network connection aware of closed socket and try to reconnect

Medium priority:
- [x] Make alt-left/right expand server list, alt-up/down skip non-expanded channels
- [x] Check if possible to synch buffer notification levels with internal weechat 
- [x] Make connection dialog behave as expected on Enter press

Low priority:
- [ ] Make things configurable using stylesheets
- [ ] Add code to fetch and display images.
- [ ] Make clicking on nick open query buffer.
- [ ] Application icon.
- [ ] Fetching additional buffer lines per request
- [ ] Look into way to speed up insert_with_tags which cause lags when 100s of lines are received

