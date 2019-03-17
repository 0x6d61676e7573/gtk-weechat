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
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from network import Network
import protocol
from buffer import Buffer#, ChatTextEdit
import config
import copy 

FUN_MSG="\n\n\n\n\n\n\n\n\n\n\n\n"\
"      _______  _________ __   ___       __         ______________        _____   \n"\
"     ___  ___\/__  __/ // /   __ |     / /___________  ____/__  /_______ __  /_  \n"\
"     __  / ___ _  / /   _/ __ __ | /| / /_  _ \  _ \  /    __  __ \  __ `/  __/  \n"\
"     ___ |_/ /_  / / /\ \     __ |/ |/ / /  __/  __/ /___  _  / / / /_/ // /_    \n"\
"      ______/ /_/ /_/ /_/     ____/|__/  \___/\___/\____/  /_/ /_/\__,_/ \__/    \n"



class MainWindow(Gtk.Window):
    """GTK Main Window."""
    """Should probably switch to GTK Application class later on, """
    """but does not matter now."""
    def __init__(self):
        Gtk.Window.__init__(self, title="Gtk-WeeChat")
        self.set_default_size(800,600)
        self.connect("destroy", Gtk.main_quit)
        
        # Get the settings from the config file
        self.config=config.read()
        
        # Set up a list of buffer objects, holding data for every buffer
        self.buffers=[Buffer()]
        
        # Set up GTK Grid
        grid=Gtk.Grid()
        grid.set_column_spacing(3)
        grid.set_row_spacing(3)
        self.add(grid)
        
        # Set up a headerbar
        self.headerbar=Gtk.HeaderBar()
        self.headerbar.set_has_subtitle(True)
        self.headerbar.set_title("Gtk-WeeChat")
        self.headerbar.set_subtitle("Not connected.")
        self.headerbar.set_show_close_button(True)
        self.set_titlebar(self.headerbar)
        
        # Set up stack of buffers
        self.stack=Gtk.Stack()
        grid.attach(self.stack,1,0,1,1)
        
        # Set up a widget to show as default in stack
        default_widget_buffer=Gtk.TextBuffer()
        default_widget_buffer.insert(default_widget_buffer.get_start_iter(),FUN_MSG)
        self.default_widget=Gtk.TextView.new_with_buffer(default_widget_buffer)
        self.default_widget.set_monospace(True)
        self.default_widget.set_hexpand(True)
        self.default_widget.set_vexpand(True)
        self.stack.add_named(self.default_widget, "default")
        self.stack.set_visible(self.default_widget)
        
        # Set up main window buttons
        button_connect=Gtk.Button(label="connect")
        button_connect.connect("clicked",self.on_button_connect_clicked)
        button_disconnect=Gtk.Button(label="disconnect")
        button_disconnect.connect("clicked",self.on_button_disconnect_clicked)
        self.headerbar.pack_start(button_connect)
        self.headerbar.pack_start(button_disconnect)
        
        # Set up widget for displaing list of chatbuffer indices + names
        self.list_buffers=Gtk.ListStore(str, str)
        self.tree=Gtk.TreeView(self.list_buffers)
        self.renderer=Gtk.CellRendererText()
        self.renderer2=Gtk.CellRendererText()
        self.column=Gtk.TreeViewColumn("Name",self.renderer,text=0)
        self.column2=Gtk.TreeViewColumn("#",self.renderer2,text=1)
        self.tree.append_column(self.column)
        self.tree.append_column(self.column2)
        self.tree.set_activate_on_single_click(True)
        self.tree.set_headers_visible(False)
        self.tree.connect("row-activated", self.on_tree_row_clicked)
        grid.attach(self.tree,0,0,1,1)
        
        # Set up the network module
        self.net=Network()
        self.net.connect("messageFromWeechat",self._network_weechat_msg)
        
    def on_button_connect_clicked(self, widget):
        """Callback function for when the connect button is clicked."""
        print("Connecting")
        self.headerbar.set_subtitle("Connecting...")
        self.net.connect_weechat()
        
    def on_button_disconnect_clicked(self, widget):
        """Callback function for when the disconnect button is clicked."""
        print("Disonnecting")
        self.net.disconnect_weechat()
        self.list_buffers.clear()
        self.stack.set_visible(self.default_widget)
        for buf in self.buffers:
            buf.widget.destroy()
        self.buffers=[]
        self.headerbar.set_title("Gtk-WeeChat")
        self.headerbar.set_subtitle("Not connected.")
        
    def on_tree_row_clicked(self, soure_object, path, column):
        """Callback for when a buffer is clicked on in the TreeView."""
        index=path.get_indices()[0]
        self.show_buffer_by_index(index)
        self.buffers[index].widget.scrollbottom()
        
    def show_buffer_by_index(self, index):
        self.buffers[index].widget.show_all()
        self.stack.set_visible_child(self.buffers[index].widget)
        self.headerbar.set_title(self.buffers[index].data["short_name"])
        self.headerbar.set_subtitle(self.buffers[index].data["title"])
        
    def on_send_message(self, source_object):
        text=copy.deepcopy(source_object.get_text()) #returned string can not be stored
        index=self.get_active_buffer()
        if index:
            full_name=self.buffers[index].data["full_name"]
            message = 'input %s %s\n' % (full_name, text)
            self.net.send_to_weechat(message)
            source_object.get_buffer().delete_text(0,-1)
            
    def _network_weechat_msg(self, source_object, message):
        """Called when a message is received from WeeChat."""
        try:
            proto = protocol.Protocol()
            if len(message.get_data()) >= 5:
                decoded_message = proto.decode(message.get_data())
                self.parse_message(decoded_message)
            else:
                print("Error, length of received message is {} bytes.".format(len(message.get_data())))
        except:  # noqa: E722
            print('Error while decoding message from WeeChat:\n%s'
                  % traceback.format_exc())
            self.net.disconnect_weechat()

    def parse_message(self, message):
        """Parse a WeeChat message."""
        if message.msgid.startswith('debug'):
            self.debug_display(0, '', '(debug message, ignored)')
        elif message.msgid == 'listbuffers':
            self._parse_listbuffers(message)
        elif message.msgid in ('listlines', '_buffer_line_added'):
            self._parse_line(message)
        elif message.msgid in ('_nicklist', 'nicklist'):
            self._parse_nicklist(message)
        elif message.msgid == '_nicklist_diff':
            self._parse_nicklist_diff(message)
        elif message.msgid == '_buffer_opened':
            self._parse_buffer_opened(message)
        elif message.msgid.startswith('_buffer_'):
            self._parse_buffer(message)
        elif message.msgid == '_upgrade':
            self.network.desync_weechat()
        elif message.msgid == '_upgrade_ended':
            self.network.sync_weechat()
            
    def _parse_listbuffers(self, message):
        """Parse a WeeChat with list of buffers."""
        for obj in message.objects:
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'buffer':
                continue
            self.list_buffers.clear()
            self.buffers = []
            for item in obj.value['items']:
                buf = self.create_buffer(item)
                self.insert_buffer(len(self.buffers), buf)
                self.stack.add_named(buf.widget, item["__path"][0])
                buf.widget.entry.connect("activate", self.on_send_message)

    def _parse_line(self, message):
        """Parse a WeeChat message with a buffer line."""
        for obj in message.objects:
            lines = []
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'line_data':
                continue
            for item in obj.value['items']:
                if message.msgid == 'listlines':
                    ptrbuf = item['__path'][0]
                else:
                    ptrbuf = item['buffer']
                index = [i for i, b in enumerate(self.buffers)
                         if b.pointer() == ptrbuf]
                if index:
                    lines.append(
                        (index[0],
                         (item['date'], item['prefix'],
                          item['message']))
                    )
### TODO: Scroll to bottom if window is in bottom state
            if message.msgid == 'listlines':
                lines.reverse()
            for line in lines:
                self.buffers[line[0]].chat.display(*line[1])
                self.buffers[line[0]].widget.scrollbottom()
                

    def _parse_nicklist(self, message):
        """Parse a WeeChat message with a buffer nicklist."""
        buffer_refresh = set()
        for obj in message.objects:
            if obj.objtype != 'hda' or \
               obj.value['path'][-1] != 'nicklist_item':
                continue
            group = '__root'
            for item in obj.value['items']:
                index = [i for i, b in enumerate(self.buffers)
                         if b.pointer() == item['__path'][0]]
                if index:
                    if not index[0] in buffer_refresh:
                        self.buffers[index[0]].nicklist = {}
                    buffer_refresh.add(index[0])
                    if item['group']:
                        group = item['name']
                    self.buffers[index[0]].nicklist_add_item(
                        group, item['group'], item['prefix'], item['name'],
                        item['visible'])
        for index in buffer_refresh:
            self.buffers[index].nicklist_refresh()
            
    def _parse_nicklist_diff(self, message):
        """Parse a WeeChat message with a buffer nicklist diff."""
        buffer_refresh = set()
        for obj in message.objects:
            if obj.objtype != 'hda' or \
               obj.value['path'][-1] != 'nicklist_item':
                continue
            group = '__root'
            for item in obj.value['items']:
                index = [i for i, b in enumerate(self.buffers)
                         if b.pointer() == item['__path'][0]]
                if not index:
                    continue
                buffer_refresh.add(index[0])
                if item['_diff'] == ord('^'):
                    group = item['name']
                elif item['_diff'] == ord('+'):
                    self.buffers[index[0]].nicklist_add_item(
                        group, item['group'], item['prefix'], item['name'],
                        item['visible'])
                elif item['_diff'] == ord('-'):
                    self.buffers[index[0]].nicklist_remove_item(
                        group, item['group'], item['name'])
                elif item['_diff'] == ord('*'):
                    self.buffers[index[0]].nicklist_update_item(
                        group, item['group'], item['prefix'], item['name'],
                        item['visible'])
        for index in buffer_refresh:
            self.buffers[index].nicklist_refresh()
            
    def _parse_buffer_opened(self, message):
        """Parse a WeeChat message with a new buffer (opened)."""
        for obj in message.objects:
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'buffer':
                continue
            for item in obj.value['items']:
                buf = self.create_buffer(item)
                index = self.find_buffer_index_for_insert(item['next_buffer'])
                print(item)
                print(buf.data["full_name"])
                print(buf.data["short_name"])
                self.insert_buffer(index, buf)
                self.stack.add_named(buf.widget, item["__path"][0])
                self.tree.get_selection().select_path(Gtk.TreePath([index]))
                self.show_buffer_by_index(index)
                

    def _parse_buffer(self, message):
        """Parse a WeeChat message with a buffer event
        (anything except a new buffer).
        """
        for obj in message.objects:
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'buffer':
                continue
            for item in obj.value['items']:
                index = [i for i, b in enumerate(self.buffers)
                         if b.pointer() == item['__path'][0]]
                if not index:
                    continue
                index = index[0]
                if message.msgid == '_buffer_type_changed':
                    self.buffers[index].data['type'] = item['type']
                elif message.msgid in ('_buffer_moved', '_buffer_merged',
                                       '_buffer_unmerged'):
                    buf = self.buffers[index]
                    buf.data['number'] = item['number']
                    self.remove_buffer(index)
                    index2 = self.find_buffer_index_for_insert(
                        item['next_buffer'])
                    self.insert_buffer(index2, buf)
                    #TODO change/updateliststore rows
                elif message.msgid == '_buffer_renamed':
                    self.buffers[index].data['full_name'] = item['full_name']
                    self.buffers[index].data['short_name'] = item['short_name']
                elif message.msgid == '_buffer_title_changed':
                    self.buffers[index].data['title'] = item['title']
                    self.update_subtitle()
                elif message.msgid == '_buffer_cleared':
                    self.buffers[index].chat.delete(
                        *self.buffers[index].chat.get_bounds())
                elif message.msgid.startswith('_buffer_localvar_'):
                    self.buffers[index].data['local_variables'] = \
                        item['local_variables']
                    pass #TODO 
                    #self.buffers[index].update_prompt()
                elif message.msgid == '_buffer_closing':
                    self.remove_buffer(index)
                    
    def create_buffer(self, item):
        """Create a new buffer."""
        buf = Buffer(item)
        return buf

    def remove_buffer(self, index):
        """Remove a buffer."""
        self.list_buffers.remove(self.list_buffers.get_iter_from_string(str(index)))
        self.buffers.pop(index)
        #TODO change selected buffer

    def insert_buffer(self, index, buf):
        """Insert a buffer in list."""
        self.buffers.insert(index, buf)
        if buf.data["short_name"]:
            name=buf.data["short_name"]
        #elif buf.data["name"]:
        #    name=buf.data["name"].split(".")[1]
        else:
            name=buf.data["full_name"]
        self.list_buffers.insert(index, (name,"[{}]".format(buf.data["number"]) ))       

    def find_buffer_index_for_insert(self, next_buffer):
        """Find position to insert a buffer in list."""
        index = -1
        if next_buffer == '0x0':
            index = len(self.buffers)
        else:
            index = [i for i, b in enumerate(self.buffers)
                     if b.pointer() == next_buffer]
            if index:
                index = index[0]
        if index < 0:
            print('Warning: unable to find position for buffer, using end of '
                  'list by default')
            index = len(self.buffers)
        return index
        
    def get_active_buffer(self):
        selection=self.tree.get_selection()
        if selection.count_selected_rows() != 1:
            print("No selected row")
            return None
        selected=selection.get_selected_rows()[1]
        if selected:
            path=selected[0]
            return path.get_indices()[0]
    #TODO 
    def update_subtitle(self):
        pass

# Start the application 
win = MainWindow()
win.show_all()
Gtk.main()
