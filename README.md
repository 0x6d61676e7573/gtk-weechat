# gtk-weechat
GTK3 client for weechat, ported from qweechat.

Dependencies:
Python>=3.0,
PyGObject

# TODO:
High priority (pre-alpha stuff):
Fix auto scroll
Fix buffer moved/closed/opened events (make sure correct buffer get focus)
Respect background + font attribute code
Keep track of connection status and display in GUI
Implement a way to change connection details and save settings
Fix disconnect code
Add header with GPL stuff + credit to original qweechat author to all files
Make window defeault size sane
Make window resizable/draggable 
Indicate buffer activity in GUI
Indicate user flags like op/voice in nicklist
Change disconnect/connect buttons to be toggled
Add autoconnect setting
Some basic keyboard shortcuts like switch buffer
Change bufferlist background color
Add option for change of color scheme



Maybe:
CHange the way to keep track of which buffer is in focus (currently done by complicated query of the treeview widget). 

Low priority (nice to have):
Make hyperlinks clickable
Add code to fetch and display images
Make clicking on nick open query buffer
Implement nick/prefix indentation
Application icon
Buffer tree instead of list
Add option to launch local weechat backend automatically and connect to it (if possible to set up relay from commandline)
Buttons for join/part, add/connect networks


