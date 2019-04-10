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
from gi.repository import Gtk, Gio
from network import Network, ConnectionStatus
import protocol
from buffer import Buffer
import config
import copy
from bufferlist import BufferList 
from connection import ConnectionSettings

FUN_MSG="\n\n\n\n\n\n\n\n\n\n\n\n"\
" _______  _________ __   ___       __         ______________        _____ \n"\
"___  ___\/__  __/ // /   __ |     / /___________  ____/__  /_______ __  /_\n"\
"__  / ___ _  / /   _/ __ __ | /| / /_  _ \  _ \  /    __  __ \  __ `/  __/\n"\
"___ |_/ /_  / / /\ \     __ |/ |/ / /  __/  __/ /___  _  / / / /_/ // /_  \n"\
" ______/ /_/ /_/ /_/     ____/|__/  \___/\___/\____/  /_/ /_/\__,_/ \__/  \n"



class MainWindow(Gtk.ApplicationWindow):
    """GTK Main Window."""
    """Should probably switch to GTK Application class later on, """
    """but does not matter now."""
    def __init__(self, config, *args, **kwargs):
        Gtk.Window.__init__(self, *args, **kwargs)
        self.set_default_size(950,700)
        #self.connect("destroy", Gtk.main_quit)
        
        # Get the settings from the config file
        self.config=config
        
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
        
        # Set up widget showing list of buffers
        grid.attach(self.buffers.treescrolledwindow,0,0,1,1)
        
        # Set up a menu
        menubutton=Gtk.MenuButton()
        self.headerbar.pack_end(menubutton)
        menu = Gtk.Menu()
        menu.set_halign(Gtk.Align(3))
        self.menuitem_connect=Gtk.MenuItem(label="Connect")
        self.menuitem_connect.connect("activate", self.on_connect_clicked)
        self.menuitem_connect.show()
        menu.append(self.menuitem_connect)
        self.menuitem_disconnect=Gtk.MenuItem(label="Disconnect")
        self.menuitem_disconnect.connect("activate", self.on_disconnect_clicked)
        self.menuitem_disconnect.set_sensitive(False)
        self.menuitem_disconnect.show()
        menu.append(self.menuitem_disconnect)
        menuitem_settings=Gtk.MenuItem(label="Connection Details")
        menuitem_settings.connect("activate", self.on_settings_clicked)
        menuitem_settings.show()
        menu.append(menuitem_settings)
        menuitem_quit=Gtk.MenuItem(label="Quit")
        menuitem_quit.set_action_name("app.quit")
        menuitem_quit.show()
        menu.append(menuitem_quit)
        menubutton.set_popup(menu)

        # Set up the network module
        self.net=Network(self.config)
        self.net.connect("messageFromWeechat",self._network_weechat_msg)
        self.net.connect("connectionChanged", self._connection_changed)
        
        # Set up actions
        action = Gio.SimpleAction.new("buffer_next", None)
        action.connect("activate", self.on_buffer_next)
        self.add_action(action)
        action = Gio.SimpleAction.new("buffer_prev", None)
        action.connect("activate", self.on_buffer_prev)
        self.add_action(action)
        
        if self.net.check_settings() is True and \
                            self.config["relay"]["autoconnect"]=="on":
            if self.net.connect_weechat() is False:
                print("Failed to connect.")
            else:
                self.menuitem_connect.set_sensitive(False)
                self.menuitem_disconnect.set_sensitive(True)
        else:
            connectionSettings.display()

    def _connection_changed(self, source_object):
        self.update_headerbar()
        if self.net.connection_status==ConnectionStatus.NOT_CONNECTED:
            self.menuitem_disconnect.set_sensitive(False)
            self.menuitem_connect.set_sensitive(True)
        elif self.net.connection_status==ConnectionStatus.CONNECTING:
            self.menuitem_disconnect.set_sensitive(True)
            self.menuitem_connect.set_sensitive(False)
        elif self.net.connection_status==ConnectionStatus.CONNECTED:
            self.menuitem_disconnect.set_sensitive(True)
            self.menuitem_connect.set_sensitive(False)
        elif self.net.connection_status==ConnectionStatus.CONNECTION_LOST:
            self.menuitem_disconnect.set_sensitive(False)
            self.menuitem_connect.set_sensitive(True)

    def on_buffer_next(self, action, param):
        current_bufptr=self.buffers.active_buffer().pointer()
        for row in self.buffers.list_buffers:
            if row[2] == current_bufptr:
                next_row=row.get_next()
                if next_row:
                    self.buffers.show(next_row[2])
                    return

    def on_buffer_prev(self, action, param):
        current_bufptr=self.buffers.active_buffer().pointer()
        for row in self.buffers.list_buffers:
            if row[2] == current_bufptr:
                prev_row=row.get_previous()
                if prev_row:
                    self.buffers.show(prev_row[2])
                    return
        
    def on_settings_clicked(self, widget):
        connectionSettings.display()
        
    def on_connect_clicked(self, widget):
        """Callback function for when the connect button is clicked."""
        if self.net.check_settings() is False:
            connectionSettings.display()
            return
        print("Connecting")
        self.buffers.clear()
        self.headerbar.set_subtitle("Connecting...")
        self.net.connect_weechat()
        
    def on_disconnect_clicked(self, widget):
        """Callback function for when the disconnect button is clicked."""
        print("Disonnecting")
        self.net.disconnect_weechat()
        self.buffers.clear()
        self.update_headerbar()
        
    def on_send_message(self, source_object, entry):
        """ Callback for when enter is pressed in entry widget """
        if self.net.connection_status != ConnectionStatus.CONNECTED:
            return
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
        if self.net.connection_status==ConnectionStatus.CONNECTED:
            if self.buffers.active_buffer() is not None: 
                self.headerbar.set_title(self.buffers.get_title())
                self.headerbar.set_subtitle(self.buffers.get_subtitle())
                return
            else:
                self.headerbar.set_subtitle("Connected")
        elif self.net.connection_status==ConnectionStatus.NOT_CONNECTED:
            self.headerbar.set_subtitle("Not connected")
        elif self.net.connection_status==ConnectionStatus.CONNECTING:
            self.headerbar.set_subtitle("Connecting...")
        elif self.net.connection_status==ConnectionStatus.CONNECTION_LOST:
            self.headerbar.set_subtitle("Connection lost")
        self.headerbar.set_title("Gtk-WeeChat")
        

class Application(Gtk.Application):
    def __init__(self, config):
        Gtk.Application.__init__(self, 
                application_id="com.github._x67616d6e7573.gtk_weechat",
                flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window=None
        self.config=config
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)
        
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.window=MainWindow(self.config, title="Gtk-Weechat", application=self)
        self.set_accels_for_action("win.buffer_next", ["<Control>Next", "<Alt>Down"])
        self.set_accels_for_action("win.buffer_prev", ["<Control>Prior", "<Alt>Up"])
    
    def do_activate(self):
        if not self.window:
            self.window=MainWindow(self.config, title="Gtk-Weechat", application=self)
        self.window.show_all()
        self.window.present()
        
    def on_quit(self, action, param):
        self.quit()
        
        
# Start the application 
config=config.read()
connectionSettings=ConnectionSettings(config)
app=Application(config)
app.run()
