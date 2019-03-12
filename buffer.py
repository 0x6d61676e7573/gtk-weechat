from gi.repository import Gtk, Gdk
import color
import config

class ChatTextEdit(Gtk.TextBuffer):
    """Textbuffer to store buffer text."""
    def __init__(self):
        Gtk.TextBuffer.__init__(self)
        
        #The default color codes
        self._textcolor = None; #self.textColor()
        self._bgcolor = None; #QtGui.QColor('#FFFFFF')
       # self._setcolorcode = {
       #     'F': (self.setTextColor, self._textcolor),
       #     'B': (self.setTextBackgroundColor, self._bgcolor)
#}

        #We need the color class that convert formatting codes in network 
        #data to codes that the parser functions in this class can handle
        self._color = color.Color(config.color_options(), False)
        
    def display(self, time, prefix, text, forcecolor=None):
        """Adds text to the buffer."""
        ### TODO: Fix so that color codes work ###
        prefix=self._color.convert(prefix)
        text=self._color.convert(text)
        if prefix:
            self._display_with_colors(prefix + " ")
            #self.insert(self.get_end_iter(), prefix + " " )
        if text:
            self._display_with_colors(text)
            #self.insert(self.get_end_iter(),text)
            if text[-1]!="\n":
                self.insert(self.get_end_iter(),"\n")
        else:
            self.insert(self.get_end_iter(),"\n")
    
    def _display_with_colors(self, string):
        items = string.split('\x01')
        for i, item in enumerate(items):
            #A Gtk.TextTag that will be used to define all text attributes
            tag=self.create_tag() 
            if i > 0 and item.startswith('('):
                pos = item.find(')')
                if pos >= 2:
                    action = item[1]
                    code = item[2:pos]
                    if action == '+':
                        # set attribute
                        self._set_attribute(code[0], True)
                    elif action == '-':
                        # remove attribute
                        self._set_attribute(code[0], False)
                    else:
                        # reset attributes and color
                        if code == 'r':
                            self._reset_attributes()
                            #self._setcolorcode[action][0](
                            #    self._setcolorcode[action][1])
                        else:
                            # set attributes + color
                            while code.startswith(('*', '!', '/', '_', '|',
                                                   'r')):
                                if code[0] == 'r':
                                    self._reset_attributes()
                #                elif code[0] in self._setfont:
                 #                   pass
                                    #self._set_attribute(
                                    #    code[0],
                                    #    not self._font[code[0]])
                                code = code[1:]
                            if code:
                                if action=="F":
                                    rgba=Gdk.RGBA() #Need a Gdk.RGBA object
                                    rgba.parse(code)
                                    tag.props.foreground_rgba=rgba
                                #self._setcolorcode[action][0](
                                #    QtGui.QColor(code))
                    item = item[pos+1:]
            if len(item) > 0:
                self.insert_with_tags(self.get_end_iter(),item, tag)

    def _reset_attributes(self):
        pass
        #self._font = {}
        #for attr in self._setfont:
        #    self._set_attribute(attr, False)

    def _set_attribute(self, attr, value):
        pass
        #self._font[attr] = value
        #self._setfont[attr](self._fontvalues[self._font[attr]][attr])
        
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