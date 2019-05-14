# gtk-weechat
GTK3 client for weechat, ported from qweechat.

Dependencies:
- Python>=3.0,
- PyGObject

# TODO:
High priority:
- [ ] Make hyperlinks clickable.
- [ ] Add a way to use dark color scheme without changing system color scheme
- [ ] Make network connection aware of closed socket and try to reconnect

Medium priority:
- [ ] Make alt-left/right expand server list, alt-up/down skip non-expanded channels
- [ ] Check if possible to make app aware of theme switch
- [ ] Check if possible to synch buffer notification levels with internal weechat 
- [ ] Make connection dialog behave as expected on Enter press

Low priority:
- [ ] Make things configurable using stylesheets
- [ ] Add code to fetch and display images.
- [ ] Make clicking on nick open query buffer.
- [ ] Application icon.
- [ ] Fetching additional buffer lines per request
- [ ] Look into way to speed up insert_with_tags which cause lags when 100s of lines are received

