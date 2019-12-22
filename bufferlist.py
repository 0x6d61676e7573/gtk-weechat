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

import re
from gi.repository import Gtk, GObject, Gdk

class BufferStore(Gtk.TreeStore):
    """ Class to hold the buffer data to be display in the left treeview widget."""
    #pylint: disable=unsubscriptable-object
    #TreeStore is subscriptable, pylint reports a false positive
    def __init__(self, *args, **kwargs):
        Gtk.TreeStore.__init__(self, *args, **kwargs)

    def get_tree_iter_from_bufptr(self, bufptr):
        """Returns TreeIter corresponding to given buffer pointer."""
        for tree_iter in self.get_all_tree_iters():
            if self[tree_iter][2] == bufptr:
                return tree_iter
        return None

    def get_path_from_bufptr(self, bufptr):
        """Returns TreePath corresponding to given buffer pointer."""
        for tree_iter in self.get_all_tree_iters():
            if self[tree_iter][2] == bufptr:
                return self.get_path(tree_iter)
        return None

    def get_all_tree_iters(self):
        """Returns a Gtk.TreeIter for each row in the TreeStore.
        Needed because default iterator only returns top level iters.
        """
        tree_iter = self.get_iter_first()
        while tree_iter is not None:
            yield tree_iter
            if self.iter_has_child(tree_iter):
                tree_iter_child = self.iter_children(tree_iter)
                while tree_iter_child is not None:
                    yield tree_iter_child
                    tree_iter_child = self.iter_next(tree_iter_child)
            tree_iter = self.iter_next(tree_iter)

    def get_next_tree_iter(self, current_bufptr):
        """Returns TreeIter corresponding to the buffer under the buffer with
        the given buffer pointer. Returns both expanded and non-expanded buffers.
        """
        for tree_iter in self.get_all_tree_iters():
            if self[tree_iter][2] == current_bufptr:
                if self.iter_has_child(tree_iter):
                    return self.iter_children(tree_iter)
                tree_iter_next = self.iter_next(tree_iter)
                if tree_iter_next is None and self.iter_depth(tree_iter) > 0:
                    tree_iter_parent = self.iter_parent(tree_iter)
                    tree_iter_next = self.iter_next(tree_iter_parent)
                return tree_iter_next
        return None

    def get_prev_tree_iter(self, current_bufptr):
        """Returns TreeIter corresponding to the buffer above the buffer with
        the given buffer pointer. Returns both expanded and non-expanded buffers.
        """
        for tree_iter in self.get_all_tree_iters():
            if self[tree_iter][2] == current_bufptr:
                tree_iter_prev = self.iter_previous(tree_iter)
                if tree_iter_prev is not None:
                    if self.iter_has_child(tree_iter_prev):
                        nbr_of_children = self.iter_n_children(tree_iter_prev)
                        tree_iter_prev = self.iter_nth_child(tree_iter_prev, nbr_of_children-1)
                    return tree_iter_prev
                return self.iter_parent(tree_iter)
        return None


class BufferList(GObject.GObject):
    """Class to integrate all buffer related data and widgets.
        Confusing index based access of buffers was abandonded
        and replaced by buffer pointers. """
    #pylint: disable=not-an-iterable, unsubscriptable-object
    #The BufferStore object is iterable and subscriptable

    __gsignals__ = {
        'bufferSwitched' : (GObject.SIGNAL_RUN_LAST, None, (str,))
        }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.buffers = []

        self.stack = Gtk.Stack()

        #Set up a default widget
        default_widget_buffer = Gtk.TextBuffer()
        self.default_widget = Gtk.TextView.new_with_buffer(default_widget_buffer)
        self.default_widget.set_hexpand(True)
        self.default_widget.set_vexpand(True)
        self.stack.add_named(self.default_widget, "default")
        self.stack.set_visible(self.default_widget)

        #Widget displaying list of buffers
        self.buffer_store = BufferStore(str, Gdk.RGBA, str)
        self.tree = Gtk.TreeView(self.buffer_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=0, foreground_rgba=1)
        self.tree.append_column(column)
        self.tree.set_activate_on_single_click(True)
        self.tree.set_headers_visible(False)
        self.tree.connect("row-activated", self.on_tree_row_clicked)
        self.treescrolledwindow = Gtk.ScrolledWindow()
        self.treescrolledwindow.add(self.tree)
        self.treescrolledwindow.set_propagate_natural_width(True)
        self.treescrolledwindow.set_min_content_width(100)
        self.tree.set_can_focus(False)

        #Dict to map pointers to buffers
        self.pointer_to_buffer_map = {}

    def __len__(self):
        return len(self.buffers)

    def __getitem__(self, index):
        return self.buffers[index]

    def __iter__(self):
        return iter(self.buffers)

    def get_expanded_nodes(self):
        """ Returns a list of all expanded top-level nodes. """
        return [node[2]
                for (i, node)
                in enumerate(self.buffer_store)
                if self.tree.row_expanded(Gtk.TreePath([i]))]

    def append(self, buf):
        """Appends a buffer to the BufferList. Finds its logical position in and inserts it to the
        bufferlist widget and adds the buffers' widget to the widget stack.
        """
        self.buffers.append(buf)
        #Find position in the list of buffers
        parent = None
        match = re.match(r"irc\.(\w+)\.#?[\S]+", buf.data.get('full_name'))
        if match is not None:
            server = match.group(1)
            parent = self.get_server_row_iter(server)
        self.buffer_store.append(
            parent, (buf.get_name(), buf.colors_for_notify["default"], buf.pointer()))
        if buf.data.get('full_name').startswith("irc") is False:
            buf.textview.set_monospace(True)
        #Add its widget to the stack
        self.stack.add_named(buf, buf.data["__path"][0])
        self.pointer_to_buffer_map[buf.pointer()] = buf
        buf.connect("notifyLevelChanged", self.on_level_changed)

    def get_server_row_iter(self, server):
        """Return treeiter to row which should be parent of buf"""
        for buf_iter in self.buffers:
            if buf_iter.data['full_name'] == "irc.server."+server:
                for row in self.buffer_store:
                    if row[2] == buf_iter.pointer():
                        return row.iter
        return None

    def clear(self):
        """Clears all data related to buffers. """
        self.stack.set_visible(self.default_widget)
        self.pointer_to_buffer_map = {}
        for buf in self.buffers:
            buf.destroy()
        self.buffers.clear()
        self.buffer_store.clear()

    def on_tree_row_clicked(self, *args):
        """Callback for when a buffer is clicked on in the TreeView. """
        path = args[1]
        bufptr = self.buffer_store[path][2]
        self.show(bufptr)

    def on_copy_to_clipboard(self, *args):
        """Callback for the copy_to_clipboard action."""
        buf = self.active_buffer()
        if buf is None:
            return
        if buf.entry.get_selection_bounds():
            buf.entry.emit("copy-clipboard")
            return
        if buf.chat.get_selection_bounds():
            buf.textview.emit("copy-clipboard")

    def show(self, bufptr):
        """ Initiates a buffer switch by emitting the bufferSwitched signal. """
        self.emit("bufferSwitched", bufptr)

    def do_bufferSwitched(self, bufptr):
        """ Switch to that buffer which pointer is provided as argument. """
        active_buf = self.active_buffer()
        if active_buf is not None:
            active_buf.active = False
        buf = self.get_buffer_from_pointer(bufptr)
        self.pointer_to_buffer_map["active"] = buf
        buf.show_all()
        self.stack.set_visible_child(buf)
        buf.entry.grab_focus()
        buf.reset_notify_level()
        path = self.buffer_store.get_path_from_bufptr(bufptr)
        if path.get_depth() > 1:
            self.tree.expand_to_path(path)
        self.tree.get_selection().select_path(path)
        buf.active = True
        buf.scrollbottom()

    def remove(self, bufptr):
        """Removes a buffer. """
        buf = self.get_buffer_from_pointer(bufptr)
        if buf is None:
            return
        if buf is self.pointer_to_buffer_map.get("active"):
            self.show(self.buffers[0].pointer())
        tree_iter = self.buffer_store.get_tree_iter_from_bufptr(bufptr)
        if tree_iter is not None:
            self.buffer_store.remove(tree_iter)
        #stack holds a reference to widget, must be explicitly destroyed
        #otherwise a name conflict occurs if the buffer is reopened
        buf.destroy()
        self.buffers.remove(buf)

    def update_buffer(self, bufptr):
        """Fetches the name and color of a buffer, given its pointer,
        and updates the bufferlist widget.
        """
        buf = self.get_buffer_from_pointer(bufptr)
        tree_iter = self.buffer_store.get_tree_iter_from_bufptr(bufptr)
        self.buffer_store[tree_iter][0:2] = (buf.get_name(), buf.get_notify_color())

    def on_level_changed(self, source_object):
        """Callback for the notifyLevelChanged signal."""
        self.update_buffer(source_object.pointer())

    def active_buffer(self):
        """Returns a pointer to the active buffer."""
        return self.pointer_to_buffer_map.get("active")

    def get_title(self):
        """Returns a title corresponding to what is currently displayed."""
        if self.active_buffer() is not None:
            return self.active_buffer().get_name()
        return "Gtk-WeeChat"

    def get_subtitle(self):
        """Returns a subtitle corresponding to what is currently displayed."""
        if self.active_buffer() is not None:
            return self.active_buffer().get_topic()
        return "Not connected."

    def get_buffer_from_pointer(self, pointer):
        """Returns a buffer, given its pointer."""
        return self.pointer_to_buffer_map.get(pointer)

    def on_buffer_next(self, *args):
        """Switches to the next unfolded buffer. """
        current_bufptr = self.active_buffer().pointer()
        tree_iter_next = self.buffer_store.get_next_tree_iter(current_bufptr)
        while tree_iter_next:
            path = self.buffer_store.get_path(tree_iter_next)
            if path.get_depth() == 2:
                path.up()
                if self.tree.row_expanded(path):
                    break
            else:
                break
            current_bufptr = self.buffer_store[tree_iter_next][2]
            tree_iter_next = self.buffer_store.get_next_tree_iter(current_bufptr)
        if tree_iter_next:
            self.show(self.buffer_store[tree_iter_next][2])

    def on_buffer_prev(self, *args):
        """Switches to the previous unfolded buffer. """
        current_bufptr = self.active_buffer().pointer()
        tree_iter_prev = self.buffer_store.get_prev_tree_iter(current_bufptr)
        while tree_iter_prev:
            path = self.buffer_store.get_path(tree_iter_prev)
            if path.get_depth() == 2:
                path.up()
                if self.tree.row_expanded(path):
                    break
            else:
                break
            current_bufptr = self.buffer_store[tree_iter_prev][2]
            tree_iter_prev = self.buffer_store.get_prev_tree_iter(current_bufptr)
        if tree_iter_prev is not None:
            self.show(self.buffer_store[tree_iter_prev][2])
