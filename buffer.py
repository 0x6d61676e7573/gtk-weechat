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

from gi.repository import Gtk, Gdk, GObject, Pango
import color
import config

class ChatTextBuffer(Gtk.TextBuffer):
    """Textbuffer to store buffer text."""
    def __init__(self, darkmode=False):
        Gtk.TextBuffer.__init__(self)
        
        #We need the color class that convert formatting codes in network 
        #data to codes that the parser functions in this class can handle
        self._color = color.Color(config.color_options(darkmode), False)
        
        #Text tags used for formatting
        bold_tag=self.create_tag(weight=Pango.Weight.BOLD)
        underline_tag=self.create_tag(underline=Pango.Underline.SINGLE)
        italic_tag=self.create_tag(style=Pango.Style.ITALIC)
        reverse_tag=self.create_tag() #reverse video is not implemented
        self.attr_tag={"*":bold_tag,"_":underline_tag,"/":italic_tag, "!":reverse_tag}

    def display(self, time, prefix, text):
        """Adds text to the buffer."""
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
        color_tag=self.create_tag() 
        attr_list=[]      
        for i, item in enumerate(items):
            if i > 0 and item.startswith('('):
                pos = item.find(')')
                if pos >= 2:
                    action = item[1]
                    code = item[2:pos]
                    if action == '+':
                        # set attribute
                        attr_list.append(self.attr_tag[code[0]])
                    elif action == '-':
                        if self.attr_tag[code[0]] in attr_list:
                            attr_list.remove(self.attr_tag[code[0]])
                    else:
                        # reset attributes and color
                        if code == 'r':
                            color_tag=self.create_tag()
                            attr_list=[]
                        else:
                            # set attributes + color
                            while code.startswith(('*', '!', '/', '_', '|',
                                                   'r')):
                                if code[0] == 'r':
                                    color_tag=self.create_tag()
                                    attr_list=[]
                                elif code[0] in self.attr_tag:
                                    attr_list.append(self.attr_tag[code[0]])
                                code = code[1:]
                            if code:
                                if action=="F":
                                    rgba=Gdk.RGBA()
                                    rgba.parse(code)
                                    color_tag=self.create_tag(foreground_rgba=rgba)
                                elif action=="B":
                                    rgba=Gdk.RGBA()
                                    rgba.parse(code)
                                    color_tag.props.background_rgba=rgba
                            else:
                                color_tag=self.create_tag() #if no color code, use a dummy tag
                    item = item[pos+1:]
            if len(item) > 0:
                self.insert_with_tags(self.get_end_iter(),item, color_tag, *attr_list)
        
class BufferWidget(Gtk.Grid):
    """Class that so far only adds a layer of indirection."""
    """In qweechat, this class also has nicklist and text entry widgets."""
    def __init__(self):
        Gtk.Grid.__init__(self)
        self.set_row_spacing(2)
        self.set_column_spacing(2)
        
        # TextView widget
        self.textview=Gtk.TextView()
        self.scrolledwindow=Gtk.ScrolledWindow()
        self.scrolledwindow.set_hexpand(True)
        self.scrolledwindow.set_vexpand(True)
        self.textview.set_cursor_visible(False)
        self.textview.set_editable(False)
        self.textview.set_can_focus(False)
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
        self.nick_display_widget.set_can_focus(False)
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
                            (Gtk.Widget,)),
        'notifyLevelChanged' : (GObject.SIGNAL_RUN_LAST, None,
                                tuple())
        }
    def __init__(self, data={}, darkmode=False):
        GObject.GObject.__init__(self)
        self.data=data
        self.nicklist={}
        self.widget=BufferWidget()
        self.widget.entry.connect("activate", self.on_send_message)
        self.nicklist_data=Gtk.ListStore(str)
        self.chat=ChatTextBuffer(darkmode)
        self.widget.textview.set_buffer(self.chat)
        self.widget.nick_display_widget.set_model(self.nicklist_data)
        styleContext=self.widget.get_style_context()
        (color_is_defined,theme_fg_color)=styleContext.lookup_color("theme_fg_color") 
        default=theme_fg_color if color_is_defined else Gdk.RGBA(0,0,0,1)
        green=Gdk.RGBA(0,0.7,0,1)
        orange=Gdk.RGBA(1,0.5,0.2,1)
        blue=Gdk.RGBA(0.2,0.2,0.7,1)
        self.colors_for_notify={"default": default, "mention":green, "message":orange, "low":blue}
        self.notify_values={"default": 0, "low": 1, "message":2, "mention":3}
        self.notify_level="default"

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
                               key=lambda n: n['name'].lower()):
                self.nicklist_data.append((nick["prefix"] + nick['name'],))
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
    
    def get_notify_color(self):
        return self.colors_for_notify[self.notify_level]

    def set_notify_level(self, notify_level):
        if self.notify_values[notify_level] > self.notify_values[self.notify_level]:
            self.notify_level=notify_level 
            self.emit("notifyLevelChanged")
    
    def reset_notify_level(self):
        self.notify_level="default"
        self.emit("notifyLevelChanged")
    
    def get_name(self):
        name = self.data["short_name"]
        if name is None:
            name = self.data["full_name"]
        return name
    
    def get_topic(self):
        return self.data["title"]
        
    def pointer(self):
        """Return pointer on buffer."""
        return self.data.get("__path",[""])[0]
