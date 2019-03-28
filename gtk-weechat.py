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
from buffer import Buffer
import config
import copy
from bufferlist import BufferList 

FUN_MSG="\n\n\n\n\n\n\n\n\n\n\n\n"\
" _______  _________ __   ___       __         ______________        _____ \n"\
"___  ___\/__  __/ // /   __ |     / /___________  ____/__  /_______ __  /_\n"\
"__  / ___ _  / /   _/ __ __ | /| / /_  _ \  _ \  /    __  __ \  __ `/  __/\n"\
"___ |_/ /_  / / /\ \     __ |/ |/ / /  __/  __/ /___  _  / / / /_/ // /_  \n"\
" ______/ /_/ /_/ /_/     ____/|__/  \___/\___/\____/  /_/ /_/\__,_/ \__/  \n"



class MainWindow(Gtk.Window):
    """GTK Main Window."""
    """Should probably switch to GTK Application class later on, """
    """but does not matter now."""
    def __init__(self):
        Gtk.Window.__init__(self, title="Gtk-WeeChat")
        self.set_default_size(950,700)
        self.connect("destroy", Gtk.main_quit)
        
        # Get the settings from the config file
        self.config=config.read()
        
        # Set up a list of buffer objects, holding data for every buffer
        self.buffers=BufferList()
        self.buffers.connect("bufferSwitched", self.on_buffer_switched)
        
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
        grid.attach(self.buffers.stack,1,0,1,1)
        
         # Set up main window buttons
        button_connect=Gtk.Button(label="connect")
        button_connect.connect("clicked",self.on_button_connect_clicked)
        button_disconnect=Gtk.Button(label="disconnect")
        button_disconnect.connect("clicked",self.on_button_disconnect_clicked)
        self.headerbar.pack_start(button_connect)
        self.headerbar.pack_start(button_disconnect)
        
        # Set up widget showing list of buffers
        grid.attach(self.buffers.treescrolledwindow,0,0,1,1)
        
        # Set up the network module
        self.net=Network()
        self.net.connect("messageFromWeechat",self._network_weechat_msg)
        if self.config["relay"]["autoconnect"]=="on":
            self.net.connect_weechat()
        
    def on_button_connect_clicked(self, widget):
        """Callback function for when the connect button is clicked."""
        print("Connecting")
        self.headerbar.set_subtitle("Connecting...")
        self.net.connect_weechat()
        
    def on_button_disconnect_clicked(self, widget):
        """Callback function for when the disconnect button is clicked."""
        print("Disonnecting")
        self.net.disconnect_weechat()
        self.buffers.clear()
        self.update_headerbar()
        
    def on_send_message(self, source_object, entry):
        """ Callback for when enter is pressed in entry widget """
        text=copy.deepcopy(entry.get_text()) #returned string can not be stored        
        full_name=source_object.data["full_name"]
        message = 'input %s %s\n' % (full_name, text)
        self.net.send_to_weechat(message)
        entry.get_buffer().delete_text(0,-1)
            
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
            self.buffers.clear()
            for item in obj.value['items']:
                buf = Buffer(item)
                self.buffers.append(buf)
                buf.connect("messageToWeechat", self.on_send_message)

    def _parse_line(self, message):
        """Parse a WeeChat message with a buffer line."""
        for obj in message.objects:
            lines = []
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'line_data':
                continue
            for item in obj.value['items']:
                notify_level="default"
                if message.msgid == 'listlines':
                    ptrbuf = item['__path'][0]
                else:
                    ptrbuf = item['buffer']
                if self.buffers.active_buffer() is not None and \
                            ptrbuf != self.buffers.active_buffer().pointer() and \
                            message.msgid != 'listlines':
                    if item["highlight"] or "notify_private" in item["tags_array"]:
                        notify_level="mention"
                    elif "notify_message" in item["tags_array"]:
                        notify_level="message"
                    else:
                        notify_level="low"
                buf = self.buffers.get_buffer_from_pointer(ptrbuf)
                if buf:
                    lines.append(
                        (ptrbuf,
                         (item['date'], item['prefix'],
                          item['message']))
                    )
                    buf.set_notify_level(notify_level)
            if message.msgid == 'listlines':
                lines.reverse()
            for line in lines:
                self.buffers.get_buffer_from_pointer(line[0]).chat.display(*line[1])
                self.buffers.get_buffer_from_pointer(line[0]).widget.scrollbottom()
            # Trying not to freeze GUI on e.g. /list:
            while Gtk.events_pending():
                Gtk.main_iteration()

    def _parse_nicklist(self, message):
        """Parse a WeeChat message with a buffer nicklist."""
        buffer_refresh = set()
        for obj in message.objects:
            if obj.objtype != 'hda' or \
               obj.value['path'][-1] != 'nicklist_item':
                continue
            group = '__root'
            for item in obj.value['items']:
                bufptr=item['__path'][0]
                buf=self.buffers.get_buffer_from_pointer(bufptr)
                if buf is not None:
                    if not buf in buffer_refresh:
                        buf.nicklist = {}
                    buffer_refresh.add(buf)
                    if item['group']:
                        group = item['name']
                    buf.nicklist_add_item(
                        group, item['group'], item['prefix'], item['name'],
                        item['visible'])
        for buf in buffer_refresh:
            buf.nicklist_refresh()
            
    def _parse_nicklist_diff(self, message):
        """Parse a WeeChat message with a buffer nicklist diff."""
        buffer_refresh = set()
        for obj in message.objects:
            if obj.objtype != 'hda' or \
               obj.value['path'][-1] != 'nicklist_item':
                continue
            group = '__root'
            for item in obj.value['items']:
                bufptr=item['__path'][0]
                buf=self.buffers.get_buffer_from_pointer(bufptr)
                if buf is None:
                    continue
                buffer_refresh.add(buf)
                if item['_diff'] == ord('^'):
                    group = item['name']
                elif item['_diff'] == ord('+'):
                    buf.nicklist_add_item(
                        group, item['group'], item['prefix'], item['name'],
                        item['visible'])
                elif item['_diff'] == ord('-'):
                    buf.nicklist_remove_item(
                        group, item['group'], item['name'])
                elif item['_diff'] == ord('*'):
                    buf.nicklist_update_item(
                        group, item['group'], item['prefix'], item['name'],
                        item['visible'])
        for buf in buffer_refresh:
            buf.nicklist_refresh()
            
    def _parse_buffer_opened(self, message):
        """Parse a WeeChat message with a new buffer (opened)."""
        for obj in message.objects:
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'buffer':
                continue
            for item in obj.value['items']:
                buf = Buffer(item)
                self.buffers.append(buf)
                buf.connect("messageToWeechat", self.on_send_message)
                self.buffers.show(buf.pointer())
                while Gtk.events_pending():
                    Gtk.main_iteration()

    def _parse_buffer(self, message):
        """Parse a WeeChat message with a buffer event
        (anything except a new buffer).
        """
        for obj in message.objects:
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'buffer':
                continue
            for item in obj.value['items']:
                bufptr=item['__path'][0]
                buf=self.buffers.get_buffer_from_pointer(bufptr)
                if buf is None:
                    continue
                if message.msgid == '_buffer_type_changed':
                    buf.data['type'] = item['type']
                elif message.msgid in ('_buffer_moved', '_buffer_merged',
                                       '_buffer_unmerged'):
                    buf.data['number'] = item['number']
                elif message.msgid == '_buffer_renamed':
                    buf.data['full_name'] = item['full_name']
                    buf.data['short_name'] = item['short_name']
                    self.buffers.update_buffer_widget(None)
                    self.update_headerbar()
                elif message.msgid == '_buffer_title_changed':
                    buf.data['title'] = item['title']
                    self.update_headerbar()
                elif message.msgid == '_buffer_cleared':
                    buf.chat.delete(
                        *self.buffers[index].chat.get_bounds())
                elif message.msgid.startswith('_buffer_localvar_'):
                    buf.data['local_variables'] = \
                        item['local_variables']
                    pass #TODO 
                    #self.buffers[index].update_prompt()
                elif message.msgid == '_buffer_closing':
                    self.buffers.remove(bufptr)

    def on_buffer_switched(self, source_object):
        """ Callback for when another buffer is switched to. """
        self.update_headerbar()
    
    def update_headerbar(self):
        """ Updates headerbar title and subtitle. """
        self.headerbar.set_title(self.buffers.get_title())
        self.headerbar.set_subtitle(self.buffers.get_subtitle())
        

# Start the application 
win = MainWindow()
win.show_all()
Gtk.main()
