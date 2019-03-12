import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from network import Network
import protocol
from buffer import Buffer, ChatTextEdit
import config

class MainWindow(Gtk.Window):
    """GTK Main Window."""
    """Should probably switch to GTK Application class later on, """
    """but does not matter now."""
    def __init__(self):
        Gtk.Window.__init__(self, title="Gtk-weechat")
        self.connect("destroy", Gtk.main_quit)
        # Get the settings from the config file
        self.config=config.read()
        
        # Set up GTK Grid
        grid=Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(grid)
        
        # Set up widget for displaying chatbuffers
        self.textview=Gtk.TextView()
        self.scrolledwindow=Gtk.ScrolledWindow()
        self.scrolledwindow.set_hexpand(True)
        self.scrolledwindow.set_vexpand(True)
        self.textview.set_cursor_visible(False)
        self.textview.set_editable(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_buffer(ChatTextEdit())
        self.scrolledwindow.add(self.textview)
        grid.attach(self.scrolledwindow,1,0,4,1)
        
        # Set up prompt
        entry=Gtk.Entry()
        grid.attach(entry,1,1,1,1)
        
        # Set up main window buttons
        button_quit = Gtk.Button(label="quit")
        button_quit.connect("clicked", self.on_button_quit_clicked)
        button_connect=Gtk.Button(label="connect")
        button_connect.connect("clicked",self.on_button_connect_clicked)
        button_disconnect=Gtk.Button(label="disconnect")
        button_disconnect.connect("clicked",self.on_button_disconnect_clicked)
        grid.attach(button_quit,2,1,1,1)
        grid.attach(button_connect,3,1,1,1)
        grid.attach(button_disconnect,4,1,1,1)
        
        # Set up widget for displaing list of chatbuffer indices + names
        self.list_buffers=Gtk.ListStore(int, str)
        self.tree=Gtk.TreeView(self.list_buffers)
        self.renderer=Gtk.CellRendererText()
        self.renderer2=Gtk.CellRendererText()
        self.column=Gtk.TreeViewColumn("#",self.renderer,text=0)
        self.column2=Gtk.TreeViewColumn("Name",self.renderer2,text=1)
        self.tree.append_column(self.column)
        self.tree.append_column(self.column2)
        self.tree.set_activate_on_single_click(True)
        self.tree.connect("row-activated", self.on_tree_row_clicked)
        grid.attach(self.tree,0,0,1,2)
        
        # Set up a list of buffer objects, holding data for every buffer
        self.buffers=[Buffer()]
        
        # Set up the network module
        self.net=Network()
        self.net.connect("messageFromWeechat",self._network_weechat_msg)

    def on_button_quit_clicked(self, widget):
        """Callback function for when the quit button is clicked."""
        Gtk.main_quit()
        
    def on_button_connect_clicked(self, widget):
        """Callback function for when the connect button is clicked."""
        print("Connecting")
        self.net.connect_weechat()
        
    def on_button_disconnect_clicked(self, widget):
        """Callback function for when the disconnect button is clicked."""
        print("Disonnecting")
        self.net.disconnect_weechat()
        
    def on_tree_row_clicked(self, soure_object, path, column):
        """Callback for when a buffer is clicked on in the TreeView."""
        index=path.get_indices()[0]
        print("Displaying buffer with index {}.".format(index))
        self.textview.set_buffer(self.buffers[index].widget.chat)
        
    def _network_weechat_msg(self, source_object, message):
        """Called when a message is received from WeeChat."""
        print("A message was receieved! / Gtk main window.")
        try:
            proto = protocol.Protocol()
            decoded_message = proto.decode(message.get_data())
            self.parse_message(decoded_message)
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
            ###SEEMS TO CLEAR STACKED BUFFERS: ###
           # while self.stacked_buffers.count() > 0:
           #     buf = self.stacked_buffers.widget(0)
           #     self.stacked_buffers.removeWidget(buf)
            self.buffers = []
            for item in obj.value['items']:
                self.list_buffers.append( (item["number"], item["full_name"]) )
                buf = self.create_buffer(item)
                self.insert_buffer(len(self.buffers), buf)
            #self.list_buffers.setCurrentRow(0)
            #self.buffers[0].widget.input.setFocus()
            
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
            if message.msgid == 'listlines':
                lines.reverse()
            for line in lines:
                self.buffers[line[0]].widget.chat.display(*line[1])


    def create_buffer(self, item):
        """Create a new buffer."""
        buf = Buffer(item)
       #buf.bufferInput.connect(self.buffer_input)
       #buf.widget.input.bufferSwitchPrev.connect(
       #     self.list_buffers.switch_prev_buffer)
       #buf.widget.input.bufferSwitchNext.connect(
       #    self.list_buffers.switch_next_buffer)
        return buf

    def insert_buffer(self, index, buf):
        """Insert a buffer in list."""
        self.buffers.insert(index, buf)
        #self.list_buffers.insertItem(index, '%d. %s'
        #                             % (buf.data['number'],
        #                                buf.data['full_name'].decode('utf-8')))
        #self.stacked_buffers.insertWidget(index, buf.widget)


# Start the application 
win = MainWindow()
win.show_all()
Gtk.main()
