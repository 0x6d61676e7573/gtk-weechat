import gi
import struct

gi.require_version('Gtk', '3.0')

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib
import sys

_PROTO_INIT_CMD = 'init password=mypass'

_PROTO_SYNC_CMDS = '(listbuffers) hdata buffer:gui_buffers(*) number,full_name,short_name,type,nicklist,title,local_variables' \
    '\n(listlines) hdata buffer:gui_buffers(*)/own_lines/last_line(-5)/'\
    'data date,displayed,prefix,message'



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
            self.input.read_bytes_async(4,0,self.cancel_network_reads,self.get_message,*user_data)
        
    def get_message(self, source_object, res, *user_data):
        """Callback function to read the first 4 bytes of message."""
        gbytes=self.input.read_bytes_finish(res)
        if gbytes == None:
            print("Thanks for nothing")
            self.input.read_bytes_async(4,0,self.cancel_network_reads,self.get_message,*user_data)
        else:
            length=struct.unpack('>i',gbytes.get_data())[0]
            print("Expecting message of size: ", length)
        self.input.read_bytes_async(length,0,self.cancel_network_reads,self.get_message_payload,*user_data)
	
    def get_message_payload(self, source_object, res, *user_data):
        """Callback function to read message from weechat of known size"""
        gbytes=self.input.read_bytes_finish(res)
        if gbytes == None:
            print("Empty message receieved...")
        else:
            print(gbytes.get_data())         
            self.emit("messageFromWeechat",gbytes)
        self.input.read_bytes_async(4,0,self.cancel_network_reads,self.get_message,*user_data)
         
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
