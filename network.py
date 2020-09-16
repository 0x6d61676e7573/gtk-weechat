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

import struct
from enum import Enum
import gi
from gi.repository import Gio, GLib, GObject
gi.require_version('Gtk', '3.0')


_PROTO_INIT_CMD = 'init password={password},compression={compression}'

_PROTO_SYNC_CMDS = '(listbuffers) hdata buffer:gui_buffers(*) number,full_name,short_name,type,nicklist,title,local_variables\n' \
    '(listlines) hdata buffer:gui_buffers(*)/own_lines/last_line(-{lines})/'\
    'data date,displayed,prefix,message,tags_array\n'\
    '(nicklist) nicklist\n'\
    'sync\n'


class ConnectionStatus(Enum):
    """Connection status definitions."""
    NOT_CONNECTED = 1
    CONNECTING = 2
    CONNECTED = 3
    CONNECTION_LOST = 4
    RECONNECTING = 5


class Network(GObject.GObject):
    """Manage network connection."""
    __gsignals__ = {"messageFromWeechat": (GObject.SIGNAL_RUN_FIRST, None, (GLib.Bytes,)),
                    "connectionChanged": (GObject.SIGNAL_RUN_FIRST, None, ())}

    def __init__(self, config):
        GObject.GObject.__init__(self)
        self.config = config
        self.cancel_network_reads = Gio.Cancellable()
        self.message_buffer = b''
        self.connection_status = ConnectionStatus.NOT_CONNECTED
        self.host = None
        self.port = None
        self.socket = None
        self.socketclient = None

    def check_settings(self):
        """ Returns True if settings required to connect are filled in. """
        return self.config.get("relay", "server") != ""\
            and self.config.get("relay", "port") != ""

    def connect_weechat(self):
        """Sets up a socket connected to the WeeChat relay."""
        if not self.check_settings():
            return False
        self.host = self.config.get("relay", "server")
        port_str = self.config.get("relay", "port")
        try:
            self.port = int(port_str)
        except ValueError:
            print("Invalid port, must be an integer.")
            return False
        network_address = Gio.NetworkAddress.new(self.host, self.port)
        self.socket = None
        self.socketclient = Gio.SocketClient.new()
        if self.config.get("relay", "ssl") == "on":
            self.socketclient.set_tls(True)
            self.socketclient.set_tls_validation_flags(Gio.TlsCertificateFlags.EXPIRED |
                                                       Gio.TlsCertificateFlags.REVOKED |
                                                       Gio.TlsCertificateFlags.INSECURE |
                                                       Gio.TlsCertificateFlags.NOT_ACTIVATED |
                                                       Gio.TlsCertificateFlags.GENERIC_ERROR)
        if self.cancel_network_reads.is_cancelled():
            self.cancel_network_reads.reset()
        self.socketclient.connect_async(
            network_address, None, self._connected_func, None)
        if self.connection_status is not ConnectionStatus.RECONNECTING:
            self.connection_status = ConnectionStatus.CONNECTING
            self.emit("connectionChanged")
        return True

    def _connected_func(self, source_object, res, *user_data):
        """Callback function called after connection attempt."""
        try:
            self.socket = self.socketclient.connect_finish(res)
        except GLib.Error as err:
            print("Connection failed:\n{}".format(err.message))
            if self.connection_status is not ConnectionStatus.RECONNECTING:
                self.connection_status = ConnectionStatus.NOT_CONNECTED
            self.emit("connectionChanged")
            return
        else:
            print("Connected")
            self.connection_status = ConnectionStatus.CONNECTED
            self.emit("connectionChanged")
            self.send_to_weechat(_PROTO_INIT_CMD.format(
                password=self.config.get("relay", "password"),
                compression="on")
                + "\n")
            self.send_to_weechat(_PROTO_SYNC_CMDS.format(
                lines=self.config.get("relay", "lines"))
                + "\n")
            self.input = self.socket.get_input_stream()
            self.input.read_bytes_async(
                4096, 0, self.cancel_network_reads, self.get_message)

    def get_message(self, source_object, res, *user_data):
        """Callback function to read network data, split it into
        WeeChat messages that are passed on to the application.
        """
        try:
            gbytes = self.input.read_bytes_finish(res)
        except GLib.Error as err:
            self.handle_network_error(err)
            return
        if gbytes is None:
            # Error, try again
            self.input.read_bytes_async(
                4096, 0, self.cancel_network_reads, self.get_message)
            return
        bytes_received = gbytes.get_size()
        if bytes_received <= 0:
            # Empty message or error, try another read
            print("Empty message error")
            return
        self.message_buffer = self.message_buffer+gbytes.get_data()
        while len(self.message_buffer) >= 4:
            length = struct.unpack('>i', self.message_buffer[0:4])[0]
            if length <= len(self.message_buffer):
                self.emit("messageFromWeechat", GLib.Bytes(
                    self.message_buffer[0:length]))
                self.message_buffer = self.message_buffer[length:]
            else:
                break
        self.input.read_bytes_async(
            4096, 0, self.cancel_network_reads, self.get_message)

    def disconnect_weechat(self):
        """Disconnect from WeeChat."""
        if not self.socket.is_connected():
            return
        else:
            self.send_to_weechat("quit\n")
            self.socket.set_graceful_disconnect(True)
            self.socket.close()
            self.socket = None
            self.cancel_network_reads.cancel()
            self.connection_status = ConnectionStatus.NOT_CONNECTED
            self.emit("connectionChanged")

    def send_to_weechat(self, message):
        """Send a message to WeeChat."""
        output = self.socket.get_output_stream()
        try:
            output.write(message.encode("utf-8"))
        except GLib.Error as err:
            self.handle_network_error(err)

    def handle_network_error(self, err):
        if err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
            print("Connection has been cancelled by user.")
            self.connection_status = ConnectionStatus.NOT_CONNECTED
            self.emit("connectionChanged")
            return
        elif err.matches(Gio.tls_error_quark(), Gio.TlsError.EOF):
            print("Server has closed the connection.")
            self.connection_status = ConnectionStatus.CONNECTION_LOST
            self.emit("connectionChanged")
            return
        elif err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.BROKEN_PIPE):
            print("Broken pipe, connection lost.")
            self.connection_status = ConnectionStatus.RECONNECTING
            self.emit("connectionChanged")
            return
        elif err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.TIMED_OUT):
            print("Connection timed out.")
            self.connection_status=ConnectionStatus.RECONNECTING
            self.emit("connectionChanged")
            return
        else:
            raise

    def desync_weechat(self):
        """Desynchronize from WeeChat."""
        self.send_to_weechat("desync\n")

    def sync_weechat(self):
        """Synchronize with WeeChat."""
        self.send_to_weechat("\n".join(_PROTO_SYNC_CMDS))

    def printdebug(self, data):
        for c in data:
            if int(c) <= 31 or (int(c) >= 128):
                print(".", end='')
            else:
                print(bytes([c]).decode("utf-8"), end='')
        print("\n")
