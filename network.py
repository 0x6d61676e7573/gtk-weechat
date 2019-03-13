import gi
import struct

gi.require_version('Gtk', '3.0')

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib
import sys

_PROTO_INIT_CMD = 'init password=mypass,compression=off'

_PROTO_SYNC_CMDS = '(listbuffers) hdata buffer:gui_buffers(*) number,full_name,short_name,type,nicklist,title,local_variables\n' \
    '(listlines) hdata buffer:gui_buffers(*)/own_lines/last_line(-80)/'\
    'data date,displayed,prefix,message\n'\
    '(nicklist) nicklist\n'\
    'sync\n'



class Network(GObject.GObject):
    __gsignals__ = { "messageFromWeechat": (GObject.SIGNAL_RUN_FIRST,None,(GLib.Bytes,))}
   
    def __init__(self):
        GObject.GObject.__init__(self)
        self.host="51.15.111.211"
        self.port=5001
        self.socket=None
        self.socketclient= Gio.SocketClient.new()
        self.adr=Gio.NetworkAddress.new(self.host,self.port)
        self.cancel_network_reads=Gio.Cancellable()
        self.message_buffer=b''
      
    def connect_weechat(self):
        """Sets up a socket connected to the WeeChat relay."""
        self.socketclient.connect_async(self.adr,None,self.connected_func,None)
      
    def connected_func(self, source_object, res, *user_data):
        """Callback function called after connection attempt."""
        self.socket=self.socketclient.connect_finish(res)
        if not self.socket:
            print("Connection failed")
        else:
            print("Connected")
            self.send_to_weechat(_PROTO_INIT_CMD+"\n")
            self.send_to_weechat(_PROTO_SYNC_CMDS+"\n")
            self.input=self.socket.get_input_stream()
            self.input.read_bytes_async(4096,0,self.cancel_network_reads,self.get_message)
        
    def get_message(self, source_object, res, *user_data):
        """Callback function to read network data, split it into"""
        """WeeChat messages that are passed on to the application."""
        gbytes=self.input.read_bytes_finish(res)
        if gbytes is None:
            #Error, try again
            self.input.read_bytes_async(4096,0,self.cancel_network_reads,self.get_message)
        bytes_received=gbytes.get_size()
        if bytes_received <=0:
            #Empty message or error, try another read
            print("Empty message error")
            return
        self.message_buffer=self.message_buffer+gbytes.get_data()
        while len(self.message_buffer)>=4:
            length=struct.unpack('>i',self.message_buffer[0:4])[0]
            if length<=len(self.message_buffer):
                self.emit("messageFromWeechat",GLib.Bytes(self.message_buffer[0:length]))
                self.message_buffer=self.message_buffer[length:]
            else:
                break
        self.input.read_bytes_async(4096,0,self.cancel_network_reads,self.get_message)
                
                
    def disconnect_weechat(self):
        """Disconnect from WeeChat."""
        if not self.socket.is_connected():
            return
        else:
            self.send_to_weechat("quit\n")
            self.socket.set_graceful_disconnect(True)
			### TODO: Make disconnect not throw exception ###
        self.cancel_network_reads.cancel()
        self.socket.close()
         
    def send_to_weechat(self,message):
        """Send a message to WeeChat."""
        output=self.socket.get_output_stream()
        output.write(message.encode("utf-8"))
		#output.flush() NOT SURE IF NEEDED
		
    def desync_weechat(self):
        """Desynchronize from WeeChat."""
        self.send_to_weechat("desync\n")
		
    def sync_weechat(self):
        """Synchronize with WeeChat."""
        self.send_to_weechat("\n".join(_PROTO_SYNC_CMDS))

    def printdebug(self,data):
        for c in data:
            if int(c) <= 31 or (int(c) >=128):
                print(".", end='')
            else:
                print(bytes([c]).decode("utf-8"), end='')
        print("\n")
                
