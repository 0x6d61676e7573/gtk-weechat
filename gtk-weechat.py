# -*- CODING: utf-8 -*-
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
import copy
import traceback
import os
import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, Gdk
from state import State
from connection import ConnectionSettings
from bufferlist import BufferList
import config
from buffer import Buffer
import protocol
from network import Network, ConnectionStatus
if sys.version_info < (3,):
    sys.exit("Requires Python version 3.0 or higher. (Version {}.{} detected)".format(
        *sys.version_info))


CONFIG_DIR = GLib.get_user_config_dir()
if not CONFIG_DIR:
    # fall back to using local directory
    CONFIG_DIR = os.path.dirname(os.path.realpath(__file__))
else:
    CONFIG_DIR = os.path.join(CONFIG_DIR, 'gtk-weechat')
    os.makedirs(CONFIG_DIR, mode=0o0755, exist_ok=True)
CONFIG_FILENAME = '%s/gtk-weechat.conf' % CONFIG_DIR

CSS_STYLE_DIR = os.path.dirname(os.path.realpath(__file__))
for dir in GLib.get_system_data_dirs():
    if os.path.exists(data_dir := os.path.join(dir, 'gtk-weechat', 'css')):
        CSS_STYLE_DIR = data_dir
# prefer styles in user data dir
if os.path.exists(user_data_dir := os.path.join(GLib.get_user_data_dir(),
                                                'gtk-weechat', 'css')):
    CSS_STYLE_DIR = user_data_dir


class MainWindow(Gtk.ApplicationWindow):
    """GTK Main Window."""

    def __init__(self, config, *args, **kwargs):
        Gtk.ApplicationWindow.__init__(self, *args, **kwargs)
        self.set_default_size(950, 700)
        self.connect("delete-event", self.on_delete_event)

        # Get the settings from the config file
        self.config = config

        # Set up a list of buffer objects, holding data for every buffer
        self.buffers = BufferList()
        self.buffers.connect("bufferSwitched", self.on_buffer_switched)
        self.buffers.connect_after(
            "bufferSwitched", self.after_buffer_switched)

        # Set up GTK box
        box_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                 spacing=0)
        self.add(box_horizontal)

        # Set up a headerbar
        self.headerbar = Gtk.HeaderBar()
        self.headerbar.set_has_subtitle(True)
        self.headerbar.set_title("Gtk-WeeChat")
        self.headerbar.set_subtitle("Not connected.")
        self.headerbar.set_show_close_button(True)
        self.set_titlebar(self.headerbar)

        # Add widget showing list of buffers
        box_horizontal.pack_start(
            self.buffers.treescrolledwindow, False, False, 0)
        sep = Gtk.Separator()
        box_horizontal.pack_start(sep, False, False, 0)

        # Add stack of buffers
        box_horizontal.pack_start(self.buffers.stack, True, True, 0)

        # Set up a menu
        menubutton = Gtk.MenuButton()
        icon = Gio.ThemedIcon(name="open-menu-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        menubutton.get_child().destroy()
        menubutton.add(image)
        menubutton.show_all()
        self.headerbar.pack_end(menubutton)
        menu = Gtk.Menu()
        menu.set_halign(Gtk.Align(3))
        menuitem_darkmode = Gtk.CheckMenuItem(label="Dark")
        menuitem_darkmode.connect("toggled", self.on_darkmode_toggled)
        menuitem_darkmode.show()
        menu.append(menuitem_darkmode)
        menu_sep = Gtk.SeparatorMenuItem()
        menu_sep.show()
        menu.append(menu_sep)
        self.menuitem_connect = Gtk.MenuItem(label="Connect")
        self.menuitem_connect.connect("activate", self.on_connect_clicked)
        self.menuitem_connect.show()
        menu.append(self.menuitem_connect)
        self.menuitem_disconnect = Gtk.MenuItem(label="Disconnect")
        self.menuitem_disconnect.connect(
            "activate", self.on_disconnect_clicked)
        self.menuitem_disconnect.set_sensitive(False)
        self.menuitem_disconnect.show()
        menu.append(self.menuitem_disconnect)
        menuitem_quit = Gtk.MenuItem(label="Quit")
        menuitem_quit.set_action_name("app.quit")
        menuitem_quit.show()
        menu.append(menuitem_quit)
        menubutton.set_popup(menu)

        # Make everything visible (All is hidden by default in GTK 3)
        self.show_all()

        # Set up the network module
        self.net = Network(self.config)
        self.net.connect("messageFromWeechat", self._network_weechat_msg)
        self.net.connect("connectionChanged", self._connection_changed)

        # Connect to connection settings signals
        CONNECTION_SETTINGS.connect("connect", self.on_settings_connect)

        # Set up actions
        action = Gio.SimpleAction.new("buffer_next", None)
        action.connect("activate", self.buffers.on_buffer_next)
        self.add_action(action)
        action = Gio.SimpleAction.new("buffer_prev", None)
        action.connect("activate", self.buffers.on_buffer_prev)
        self.add_action(action)
        action = Gio.SimpleAction.new("copy_to_clipboard", None)
        action.connect("activate", self.buffers.on_copy_to_clipboard)
        self.add_action(action)
        action = Gio.SimpleAction.new("buffer_expand", None)
        action.connect("activate", self.on_buffer_expand)
        self.add_action(action)
        action = Gio.SimpleAction.new("buffer_collapse", None)
        action.connect("activate", self.on_buffer_collapse)
        self.add_action(action)

        # Autoconnect if necessary
        if self.net.check_settings() is True and \
                            self.config["relay"]["autoconnect"] == "on":
            if self.net.connect_weechat() is False:
                print("Failed to connect.")
            else:
                self.menuitem_connect.set_sensitive(False)
                self.menuitem_disconnect.set_sensitive(True)
        else:
            CONNECTION_SETTINGS.display()

        # Enable darkmode if enabled before
        self.dark_fallback_provider = Gtk.CssProvider()
        self.dark_fallback_provider.load_from_path(
            "{}/dark_fallback.css".format(CSS_STYLE_DIR))
        if STATE.get_dark():
            menuitem_darkmode.set_active(True)

        # Sync our local hotlist with the weechat server
        GLib.timeout_add_seconds(60, self.request_hotlist)

    def on_darkmode_toggled(self, source_object):
        """Callback for when the menubutton Dark is toggled. """
        settings = Gtk.Settings().get_default()
        dark = source_object.get_active()
        if settings.props.gtk_theme_name == "Adwaita":
            if dark:
                settings.props.gtk_application_prefer_dark_theme = True
            else:
                settings.props.gtk_application_prefer_dark_theme = False
        else:
            # Non-standard theme, use fallback style provider
            style_context = self.get_style_context()
            screen = Gdk.Screen().get_default()
            if dark:
                style_context.add_provider_for_screen(
                    screen, self.dark_fallback_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
            else:
                style_context.remove_provider_for_screen(
                    screen, self.dark_fallback_provider)
        for buf in self.buffers:
            buf.update_buffer_default_color()
            buf.emit("notifyLevelChanged")
        STATE.set_dark(dark)

    def request_hotlist(self):
        """" Ask server to send a hotlist. """
        if self.net.connection_status is ConnectionStatus.CONNECTED:
            self.net.send_to_weechat(
                "(hotlist) hdata hotlist:gui_hotlist(*)\n")
        return True

    def on_delete_event(self, *args):
        """Callback function to save buffer state when window is closed."""
        self.save_expanded_buffers()

    def expand_buffers(self):
        """Check which nodes were expanded last time when state was saved,
        and expands them.
        """
        for buf_ptr in STATE.get_expanded_nodes():
            path = self.buffers.buffer_store.get_path_from_bufptr(buf_ptr)
            if path:
                self.buffers.tree.expand_row(path, False)

    def save_expanded_buffers(self):
        """Saves the list of expanded buffers."""
        STATE.set_expanded_nodes(self.buffers.get_expanded_nodes())

    def on_settings_connect(self, *args):
        """Callback for the menubutton connect."""
        if self.net.check_settings() is False:
            CONNECTION_SETTINGS.display()
            return
        if self.net.connection_status in (ConnectionStatus.NOT_CONNECTED,
                                          ConnectionStatus.CONNECTION_LOST):
            self.net.connect_weechat()
        elif self.net.connection_status in (ConnectionStatus.CONNECTED,
                                            ConnectionStatus.CONNECTING):
            self.net.disconnect_weechat()
            self.net.connect_weechat()

    def _connection_changed(self, *args):
        """Callback for when the network module reports a changed state."""
        self.update_headerbar()
        if self.net.connection_status == ConnectionStatus.NOT_CONNECTED:
            self.menuitem_disconnect.set_sensitive(False)
            self.menuitem_connect.set_sensitive(True)
        elif self.net.connection_status == ConnectionStatus.CONNECTING:
            self.menuitem_disconnect.set_sensitive(True)
            self.menuitem_connect.set_sensitive(False)
        elif self.net.connection_status == ConnectionStatus.CONNECTED:
            self.menuitem_disconnect.set_sensitive(True)
            self.menuitem_connect.set_sensitive(False)
        elif self.net.connection_status == ConnectionStatus.CONNECTION_LOST:
            self.save_expanded_buffers()
            self.menuitem_disconnect.set_sensitive(False)
            self.menuitem_connect.set_sensitive(True)
        elif self.net.connection_status == ConnectionStatus.RECONNECTING:
            self.menuitem_disconnect.set_sensitive(False)
            self.menuitem_connect.set_sensitive(False)
            self.save_expanded_buffers()
            print("Reconnecting in 5 seconds...")
            # Lambda function makes sure we only connect once
            GLib.timeout_add_seconds(
                5, lambda: self.net.connect_weechat() and False)

    def on_connect_clicked(self, *args):
        """Callback function for when the connect button is clicked."""
        CONNECTION_SETTINGS.display()

    def on_disconnect_clicked(self, *args):
        """Callback function for when the disconnect button is clicked."""
        print("Disonnecting")
        self.net.disconnect_weechat()
        self.buffers.clear()
        self.update_headerbar()

    def on_send_message(self, source_object, entry):
        """ Callback for when enter is pressed in entry widget """
        if self.net.connection_status != ConnectionStatus.CONNECTED:
            return
        # returned string can not be stored
        text = copy.deepcopy(entry.get_text())
        full_name = source_object.data["full_name"]
        message = 'input %s %s\n' % (full_name, text)
        self.net.send_to_weechat(message)
        entry.get_buffer().delete_text(0, -1)

    def _network_weechat_msg(self, source_object, message):
        """Called when a message is received from WeeChat."""
        # pylint: disable=bare-except
        try:
            proto = protocol.Protocol()
            if len(message.get_data()) >= 5:
                decoded_message = proto.decode(message.get_data())
                self.parse_message(decoded_message)
            else:
                print("Error, length of received message is {} bytes.".format(
                    len(message.get_data())))
        except:
            print('Error while decoding message from WeeChat:\n%s'
                  % traceback.format_exc())
            self.net.disconnect_weechat()

    def parse_message(self, message):
        """Parse a WeeChat message."""
        if message.msgid.startswith('debug'):
            pass
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
            self.net.desync_weechat()
        elif message.msgid == '_upgrade_ended':
            self.net.sync_weechat()
        elif message.msgid == 'hotlist':
            self._parse_hotlist(message)

    def _parse_listbuffers(self, message):
        """Parse a WeeChat with list of buffers."""
        for obj in message.objects:
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'buffer':
                continue
            self.buffers.clear()
            for item in obj.value['items']:
                buf = Buffer(self.config, item)
                self.buffers.append(buf)
                buf.connect("messageToWeechat", self.on_send_message)
                active_node = STATE.get_active_node()
                if buf.pointer() == active_node:
                    self.buffers.show(buf.pointer())
        self.expand_buffers()
        self.request_hotlist()

    def _parse_line(self, message):
        """Parse a WeeChat message with a buffer line."""
        for obj in message.objects:
            lines = []
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'line_data':
                continue
            for item in obj.value['items']:
                notify_level = "default"
                if message.msgid == 'listlines':
                    ptrbuf = item['__path'][0]
                else:
                    ptrbuf = item['buffer']
                if (self.buffers.active_buffer() is not None and
                    ptrbuf != self.buffers.active_buffer().pointer() and
                    message.msgid != 'listlines'):
                    if item["highlight"] or "notify_private" in item["tags_array"]:
                        notify_level = "mention"
                    elif "notify_message" in item["tags_array"]:
                        notify_level = "message"
                    else:
                        notify_level = "low"
                buf = self.buffers.get_buffer_from_pointer(ptrbuf)
                if buf:
                    lines.append(
                        (ptrbuf,
                         (item['date'], item['prefix'],
                          item['message'], item['tags_array']))
                    )
                    buf.set_notify_level(notify_level)
            if message.msgid == 'listlines':
                lines.reverse()
            for line in lines:
                self.buffers.get_buffer_from_pointer(line[0]).chat.display(*line[1])
                self.buffers.get_buffer_from_pointer(line[0]).scrollbottom()
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
                bufptr = item['__path'][0]
                buf = self.buffers.get_buffer_from_pointer(bufptr)
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
                bufptr = item['__path'][0]
                buf = self.buffers.get_buffer_from_pointer(bufptr)
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
                buf = Buffer(self.config, item)
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
                bufptr = item['__path'][0]
                buf = self.buffers.get_buffer_from_pointer(bufptr)
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
                    self.buffers.update_buffer(bufptr)
                    self.update_headerbar()
                elif message.msgid == '_buffer_title_changed':
                    buf.data['title'] = item['title']
                    self.update_headerbar()
                elif message.msgid == '_buffer_cleared':
                    buf.clear()
                elif message.msgid.startswith('_buffer_localvar_'):
                    buf.data['local_variables'] = \
                        item['local_variables']
                elif message.msgid == '_buffer_closing':
                    self.buffers.remove(bufptr)

    def _parse_hotlist(self, message):
        """Parse a WeeChat hotlist."""
        for buf in self.buffers:
            buf.reset_notify_level()
        for obj in message.objects:
            if not obj.value['path']:
                continue
            if obj.objtype != 'hda' or obj.value['path'][-1] != 'hotlist':
                continue
            for item in obj.value['items']:
                priority = item["priority"]
                buf = self.buffers.get_buffer_from_pointer(item["buffer"])
                if not buf:
                    continue
                if buf is self.buffers.active_buffer():
                    continue
                if priority == 0:
                    buf.set_notify_level("low")
                elif priority == 1:
                    buf.set_notify_level("message")
                elif priority == 2:
                    buf.set_notify_level("mention")
                elif priority == 3:
                    buf.set_notify_level("mention")

    def on_buffer_switched(self, source_object, bufptr):
        """ Called right before another buffer is switched to. """
        if self.buffers.active_buffer():
            cmd = "input {name} /buffer set hotlist -1\n".format(
                name=self.buffers.active_buffer().data["full_name"])
            self.net.send_to_weechat(cmd)

    def after_buffer_switched(self, source_object, bufptr):
        """ Called right after another buffer is switched to. """
        self.update_headerbar()
        if self.buffers.active_buffer():
            STATE.set_active_node(self.buffers.active_buffer().pointer())

    def on_buffer_expand(self, *args):
        """ Expand the currently selected server branch in buffer list. """
        bufptr = self.buffers.active_buffer().pointer()
        path = self.buffers.buffer_store.get_path_from_bufptr(bufptr)
        if path:
            self.buffers.tree.expand_row(path, False)

    def on_buffer_collapse(self, *args):
        """ Collapse the currently selected server branch in buffer list. """
        bufptr = self.buffers.active_buffer().pointer()
        path = self.buffers.buffer_store.get_path_from_bufptr(bufptr)
        if path:
            if path.get_depth() == 1:
                self.buffers.tree.collapse_row(path)
            else:
                path.up()
                # pylint: disable=unsubscriptable-object
                # buffer_store is a Gtk.TreeStore derived class
                self.buffers.show(self.buffers.buffer_store[path][2])
                self.buffers.tree.collapse_row(path)

    def update_headerbar(self):
        """ Updates headerbar title and subtitle. """
        if self.net.connection_status == ConnectionStatus.CONNECTED:
            if self.buffers.active_buffer() is not None:
                self.headerbar.set_title(self.buffers.get_title())
                self.headerbar.set_subtitle(self.buffers.get_subtitle())
                return
            self.headerbar.set_subtitle("Connected")
        elif self.net.connection_status == ConnectionStatus.NOT_CONNECTED:
            self.headerbar.set_subtitle("Not connected")
        elif self.net.connection_status == ConnectionStatus.CONNECTING:
            self.headerbar.set_subtitle("Connecting...")
        elif self.net.connection_status == ConnectionStatus.CONNECTION_LOST:
            self.headerbar.set_subtitle("Connection lost")
        self.headerbar.set_title("Gtk-WeeChat")


class Application(Gtk.Application):
    """Gtk Application."""
    def __init__(self, config):
        Gtk.Application.__init__(
            self, application_id="com.github._x67616d6e7573.gtk_weechat",
            flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.config = config
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.window = MainWindow(self.config, title="Gtk-Weechat", application=self)
        self.set_accels_for_action("win.buffer_next", ["<Control>Next", "<Alt>Down"])
        self.set_accels_for_action("win.buffer_prev", ["<Control>Prior", "<Alt>Up"])
        self.set_accels_for_action("win.buffer_expand", ["<Alt>Right"])
        self.set_accels_for_action("win.buffer_collapse", ["<Alt>Left"])
        self.set_accels_for_action("win.copy_to_clipboard", ["<Control>c"])

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self.config, title="Gtk-Weechat", application=self)
        self.window.present()

    def on_quit(self, *args):
        """Callback for the quit action."""
        self.window.save_expanded_buffers()
        self.quit()


# Start the application
CONFIG = config.read()
CONNECTION_SETTINGS = ConnectionSettings(CONFIG)
STATE = State("data.pickle")
STATE.load_from_file()
APP = Application(CONFIG)
APP.run()
STATE.dump_to_file()
