from gi.repository import Gtk
import color
import config

class ChatTextEdit(Gtk.TextBuffer):
    """Textbuffer to store buffer text."""
    def __init__(self):
        Gtk.TextBuffer.__init__(self)

        #We need the color class that convert formatting codes in network 
        #data to codes that the parser functions in this class can handle
        self._color = color.Color(config.color_options(), False)
        
    def display(self, time, prefix, text, forcecolor=None):
        """Adds text to the buffer."""
        ### TODO: Fix so that color codes work ###
        prefix=self._color.convert(prefix)
        text=self._color.convert(text)
        if prefix:
            self.insert(self.get_end_iter(), prefix + " | " )
        self.insert(self.get_end_iter(),text +"\n")

class BufferWidget():
    """Class that so far only adds a layer of indirection."""
    """In qweechat, this class also has nicklist and text entry widgets."""
    def __init__(self):
        self.chat=ChatTextEdit()

class Buffer:
    """A WeeChat buffer that holds buffer data."""
    def __init__(self, data={}):
        self.data=data
        self.nicklist={}
        self.widget=BufferWidget()
      
    def pointer(self):
        """Return pointer on buffer."""
        return self.data.get("__path",[""])[0]
