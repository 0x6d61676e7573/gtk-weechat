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

from gi.repository import Gtk
import config

class ConnectionSettings(Gtk.Window):
    def __init__(self, config):
        Gtk.Window.__init__(self, title="Connection")
        self.set_modal(True)
        self.set_keep_above(True)
        self.config=config
        #self.set_default_size(600,600)
        self.connect("destroy", self.on_cancel)
        grid=Gtk.Grid()
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        grid.set_margin_end(20)
        grid.set_margin_start(20)
        grid.set_margin_top(20)
        grid.set_margin_bottom(20)
        self.add(grid)
        label_names=["Host", "Port", "Password", "SSL", "Autoconnect"]
        for n, name in enumerate(label_names):
            label=Gtk.Label(name)
            label.set_halign(Gtk.Align(2))
            grid.attach(label, 0,n,1,1)
        
        self.entry1=Gtk.Entry()
        grid.attach(self.entry1,1,0,1,1)
        
        self.entry2=Gtk.Entry()
        grid.attach(self.entry2,1,1,1,1)
                
        self.entry3=Gtk.Entry()
        self.entry3.set_visibility(False)
        grid.attach(self.entry3,1,2,1,1)
        
        switch1_box=Gtk.Box()
        switch2_box=Gtk.Box()
        self.switch1=Gtk.Switch()
        self.switch2=Gtk.Switch()
        grid.attach(switch1_box, 1,3,1,1)
        grid.attach(switch2_box, 1,4,1,1)
        switch1_box.pack_start(self.switch1, False, False, 0)
        switch2_box.pack_start(self.switch2, False, False, 0)
        button_box=Gtk.Box(spacing=10)
        
        grid.attach(button_box,0,5,2,1)
        save_button=Gtk.Button(label="Save")
        cancel_button=Gtk.Button(label="Cancel")
        button_box.pack_end(save_button, False, False, 0)
        button_box.pack_end(cancel_button, False, False, 0)
        
        cancel_button.connect("clicked", self.on_cancel)
        save_button.connect("clicked", self.on_saved)
        
    def display(self):
        self.show_all()
        self.fill_in_settings()

    def on_cancel(self, widget):
        self.hide()
    
    def on_saved(self, widget):
        self.config["relay"]["server"]=self.entry1.get_text()
        self.config["relay"]["port"]=self.entry2.get_text()
        self.config["relay"]["password"]=self.entry3.get_text()
        self.config["relay"]["ssl"]= "on" if self.switch1.get_active() else "off"
        self.config["relay"]["autoconnect"]= "on" if self.switch2.get_active() else "off"
        config.write(self.config)

    def fill_in_settings(self):
        self.entry1.set_text(self.config["relay"]["server"])
        self.entry2.set_text(self.config["relay"]["port"])
        self.entry3.set_text(self.config["relay"]["password"])
        
        self.switch1.set_active(True if self.config["relay"]["ssl"] == "on" else False)
        self.switch2.set_active(True if self.config["relay"]["autoconnect"] == "on" else False)
