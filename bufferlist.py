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

from gi.repository import Gtk, GObject

class BufferList(GObject.GObject):
    """Class to integrate all buffer related data and widgets.
        Confusing index based access of buffers was abandonded
        and replaced by buffer pointers. """
        
    __gsignals__ = {
        'bufferSwitched' : (GObject.SIGNAL_RUN_LAST, None, tuple())
        }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.buffers=[]

        self.stack=Gtk.Stack()
        
        #set up a default widget
        default_widget_buffer=Gtk.TextBuffer()
        #default_widget_buffer.insert(default_widget_buffer.get_start_iter(),FUN_MSG)
        self.default_widget=Gtk.TextView.new_with_buffer(default_widget_buffer)
        #self.default_widget.set_monospace(True)
        self.default_widget.set_hexpand(True)
        self.default_widget.set_vexpand(True)
        self.stack.add_named(self.default_widget, "default")
        self.stack.set_visible(self.default_widget)
    
        #Widget displaying list of buffers:
        self.list_buffers=Gtk.ListStore(str, str, str)
        self.tree=Gtk.TreeView(self.list_buffers)
        self.renderer=Gtk.CellRendererText()
        self.column=Gtk.TreeViewColumn("Name",self.renderer,text=0, foreground=1)
        self.tree.append_column(self.column)
        self.tree.set_activate_on_single_click(True)
        self.tree.set_headers_visible(False)
        self.tree.connect("row-activated", self.on_tree_row_clicked)
        self.treescrolledwindow=Gtk.ScrolledWindow()
        self.treescrolledwindow.add(self.tree)
        self.treescrolledwindow.set_propagate_natural_width(True)
        self.treescrolledwindow.set_min_content_width(100)
        self.tree.set_can_focus(False)

        #Dict to map pointers to buffers
        self.pointer_to_buffer_map = {}
        
    def __len__(self):
        return len(self.buffers)
        
    def __getitem__(self, n):
        return self.buffers[n]
    
    def __iter__(self):
        return iter(self.buffers)
    
    def append(self, buf):
        self.buffers.append(buf)
        self.list_buffers.append((buf.get_name(),buf.colors_for_notify["default"], buf.pointer()))
        self.stack.add_named(buf.widget, buf.data["__path"][0])
        self.pointer_to_buffer_map[buf.pointer()]=buf
        buf.connect("notifyLevelChanged", self.update_buffer_widget)
        
    def clear(self):
        """ Clears all data related to buffers. """
        self.stack.set_visible(self.default_widget)
        self.pointer_to_buffer_map={}
        for buf in self.buffers:
            buf.widget.destroy()
        self.buffers.clear()
        self.list_buffers.clear()
        
    def on_tree_row_clicked(self, source_object, path, column):
        """ Callback for when a buffer is clicked on in the TreeView. """
        index=path.get_indices()[0]
        bufptr=self.list_buffers[index][2]
        self.show(bufptr)
    
    def show(self, bufptr):
        """ Shows a buffer in the main window given its pointer. """
        buf=self.get_buffer_from_pointer(bufptr)
        self.pointer_to_buffer_map["active"]=buf
        buf.widget.show_all()
        self.stack.set_visible_child(buf.widget)
        buf.widget.scrollbottom()
        buf.widget.entry.grab_focus()
        buf.reset_notify_level()
        self.emit("bufferSwitched")
        
    def remove(self, bufptr):
        buf=self.get_buffer_from_pointer(bufptr)
        if buf is None:
            return
        if buf is self.pointer_to_buffer_map.get("active"):
            self.show(self.buffers[0].pointer())
        #stack holds a reference to widget, must be explicitly destroyed
        #otherwise a name conflict occurs if the buffer is reopened
        buf.widget.destroy()
        self.buffers.remove(buf)
        self.update_buffer_widget(None)
        
        
    def update_buffer_widget(self, source_object):
        self.list_buffers.clear()
        for buf in self.buffers:
            self.list_buffers.append((buf.get_name(),buf.notify_color(), buf.pointer()))
        if self.active_buffer() is not None:
            buf=self.active_buffer()
            self.tree.get_selection().select_path(Gtk.TreePath([self.buffers.index(buf)]))
    
    def active_buffer(self):
        return self.pointer_to_buffer_map.get("active")
    
    def get_title(self):
        if self.active_buffer() is not None:
            return self.active_buffer().get_name()
        else:
            return "Gtk-WeeChat"
    
    def get_subtitle(self):
        if self.active_buffer() is not None:
            return self.active_buffer().get_topic()
        else:
            return "Not connected."
    
    def get_buffer_from_pointer(self, pointer):
        return self.pointer_to_buffer_map.get(pointer)

        
