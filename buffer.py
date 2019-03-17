# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2019 Sébastien Helleu <flashcode@flashtux.org>
#
# This file is part of QWeeChat, a Qt remote GUI for WeeChat.
#
# QWeeChat is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# QWeeChat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with QWeeChat.  If not, see <http://www.gnu.org/licenses/>.
#

from gi.repository import Gtk, Gdk, GObject
import color
import config

class ChatTextBuffer(Gtk.TextBuffer):
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
        
class BufferWidget(Gtk.Grid):
    """Class that so far only adds a layer of indirection."""
    """In qweechat, this class also has nicklist and text entry widgets."""
    def __init__(self):
        Gtk.Grid.__init__(self)
        
        # TextView widget
        self.textview=Gtk.TextView()
        self.scrolledwindow=Gtk.ScrolledWindow()
        self.scrolledwindow.set_hexpand(True)
        self.scrolledwindow.set_vexpand(True)
        self.textview.set_cursor_visible(False)
        self.textview.set_editable(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_monospace(True)
        self.scrolledwindow.add(self.textview)
        self.attach(self.scrolledwindow,0,0,1,1)
        self.adjustment=self.textview.get_vadjustment()
        
        # Entry widget
        self.entry=Gtk.Entry()
        self.attach(self.entry,0,1,2,1)
        
        # Nicklist widget
        nicklist_renderer=Gtk.CellRendererText()
        nicklist_column=Gtk.TreeViewColumn("",nicklist_renderer,text=0)
        self.nick_display_widget=Gtk.TreeView()
        self.nick_display_widget.set_headers_visible(False)
        self.nick_display_widget.append_column(nicklist_column)
        scrolledwindow=Gtk.ScrolledWindow()
        scrolledwindow.set_propagate_natural_width(True)
        scrolledwindow.add(self.nick_display_widget)
        self.attach(scrolledwindow,1,0,1,1)
        
    def scrollbottom(self):
        """Scrolls textview widget to it's bottom state."""
        value=self.adjustment.get_upper()-self.adjustment.get_page_size()
        self.adjustment.set_value(value)

        
class Buffer(GObject.GObject):
    """A WeeChat buffer that holds buffer data."""
    __gsignals__ = {
        'messageToWeechat' : (GObject.SIGNAL_RUN_LAST, None,
                            (Gtk.Widget,))
        }
    def __init__(self, data={}):
        GObject.GObject.__init__(self)
        self.data=data
        self.nicklist={}
        self.widget=BufferWidget()
        self.widget.entry.connect("activate", self.on_send_message)
        self.nicklist_data=Gtk.ListStore(str)
        self.chat=ChatTextBuffer()
        self.widget.textview.set_buffer(self.chat)
        self.widget.nick_display_widget.set_model(self.nicklist_data)
    
    def nicklist_add_item(self, parent, group, prefix, name, visible):
        """Add a group/nick in nicklist."""
        if group:
            self.nicklist[name] = {
                'visible': visible,
                'nicks': []
            }
        else:
            self.nicklist[parent]['nicks'].append({
                'prefix': prefix,
                'name': name,
                'visible': visible,
            })
    
    def nicklist_refresh(self):
        """Refresh nicklist."""
        self.nicklist_data.clear()
        for group in sorted(self.nicklist):
            for nick in sorted(self.nicklist[group]['nicks'],
                               key=lambda n: n['name']):
                self.nicklist_data.append((nick['name'],))
              #  prefix_color = {
              #      '': '',
              #      ' ': '',
              #      '+': 'yellow',
              #  }
                #color = prefix_color.get(nick['prefix'], 'green')
                #if color:
                #    icon = QtGui.QIcon(
                 #       resource_filename(__name__,
                 #                         'data/icons/bullet_%s_8x8.png' %
                 #                         color))
               # else:
                  #  pixmap = QtGui.QPixmap(8, 8)
                   # pixmap.fill()
                   # icon = QtGui.QIcon(pixmap)
                #item = QtGui.QListWidgetItem(icon, nick['name'])
                #self.widget.nicklist.addItem(item)
        #self.widget.nicklist.setVisible(True)
        
    def nicklist_remove_item(self, parent, group, name):
        """Remove a group/nick from nicklist."""
        if group:
            if name in self.nicklist:
                del self.nicklist[name]
        else:
            if parent in self.nicklist:
                self.nicklist[parent]['nicks'] = [
                    nick for nick in self.nicklist[parent]['nicks']
                    if nick['name'] != name
                ]

    def nicklist_update_item(self, parent, group, prefix, name, visible):
        """Update a group/nick in nicklist."""
        if group:
            if name in self.nicklist:
                self.nicklist[name]['visible'] = visible
        else:
            if parent in self.nicklist:
                for nick in self.nicklist[parent]['nicks']:
                    if nick['name'] == name:
                        nick['prefix'] = prefix
                        nick['visible'] = visible
                        break
                        
    def on_send_message(self, source_object):
        self.emit("messageToWeechat", source_object)

    def pointer(self):
        """Return pointer on buffer."""
        return self.data.get("__path",[""])[0]
