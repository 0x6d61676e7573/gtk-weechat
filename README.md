# gtk-weechat
GTK3 client for weechat, ported from qweechat.

Dependencies:
Python>=3.0,
PyGObject

# TODO:
High priority:
Fix broken auto scroll
Tab completion
Add time info

Medium priority:
Make hyperlinks clickable.
Make alt-left/right expand server list, alt-up/down skip non-expanded channels
Check if possible to make app aware of theme switch
Make network connection aware of closed socket and try to reconnect
Check if possible to synch buffer notification levels with internal weechat 
Add a way to use dark color scheme without changing system color scheme
Make connection dialog behave as expected on Enter press

Low priority:
Make things configurable using stylesheets
Add code to fetch and display images.
Make clicking on nick open query buffer.
Application icon.
Fetching additional buffer lines per request
Look into way to speed up insert_with_tags which cause lags when 100s of lines are received

