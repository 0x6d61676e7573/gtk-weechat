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

from enum import Enum
import re
import datetime
from gi.repository import Gtk, Gdk, GObject, Pango
import color

URL_PATTERN = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")


class MessageType(Enum):
    """Definition of message types."""
    SERVER_MESSAGE = 0
    CHAT_MESSAGE = 1
    TIME_STAMP = 2


class ChatTextBuffer(Gtk.TextBuffer):
    """Textbuffer to store buffer text."""

    def __init__(self, config, layout=None):
        Gtk.TextBuffer.__init__(self)
        self.config = config
        self.layout = layout
        self.last_prefix = None
        self.last_message_type = None
        self.longest_prefix = 0
        self.indent_tag_list = []
        self.d_previous = datetime.datetime.fromtimestamp(0)

        # We need the color class that convert formatting codes in network
        # data to codes that the parser functions in this class can handle
        self._color = color.Color(config.color_options(), False)

        # Text tags used for formatting
        self.time_tag = self.create_tag(
            justification=Gtk.Justification.RIGHT, weight=Pango.Weight.BOLD)
        bold_tag = self.create_tag(weight=Pango.Weight.BOLD)
        underline_tag = self.create_tag(underline=Pango.Underline.SINGLE)
        italic_tag = self.create_tag(style=Pango.Style.ITALIC)
        reverse_tag = self.create_tag()  # reverse video is not implemented
        self.attr_tag = {"*": bold_tag, "_": underline_tag,
                         "/": italic_tag, "!": reverse_tag}
        self.url_tag = self.create_tag(underline=Pango.Underline.SINGLE)

    def display(self, time, prefix, text, tags_array):
        """Adds text to the buffer."""
        message_type = self.get_message_type(tags_array)
        prefix = self._color.convert(prefix)
        text = self._color.convert(text)
        has_prefix = False
        if time == 0:
            d = datetime.datetime.now()
        else:
            d = datetime.datetime.fromtimestamp(float(time))
        delta = d-self.d_previous
        if delta.total_seconds() >= 5*60 and message_type != MessageType.SERVER_MESSAGE and prefix != self.last_prefix:
            self.insert_with_tags(self.get_end_iter(), d.strftime(
                self.config.get('look', 'buffer_time_format')) + "\n",
                self.time_tag)
            self.last_message_type = MessageType.TIME_STAMP
            self.d_previous = d

        if prefix is not None and prefix != self.last_prefix:
            if message_type == MessageType.SERVER_MESSAGE:
                prefix = prefix.replace("-->", "\u27F6")
                prefix = prefix.replace("<--", "\u27F5")
                prefix = prefix.replace("--", "\u2014")
            self.last_prefix = prefix
            self._display_with_colors(
                prefix + " ", indent="prefix", msg_type=message_type)
            has_prefix = True
        if text:
            self._display_with_colors(
                text, indent="no_prefix" if has_prefix == False else "text", msg_type=message_type)
            if text[-1] != "\n":
                self.insert(self.get_end_iter(), "\n")
        else:
            self.insert(self.get_end_iter(), "\n")
        self.last_message_type = message_type

    def _display_with_colors(self, string, indent=False, msg_type=MessageType.CHAT_MESSAGE):
        indent_tag = self.create_tag()
        self.indent_tag_list.append(indent_tag)
        items = string.split('\x01')
        color_tag = self.create_tag()
        attr_list = []
        stripped_items = []
        # The way split works, the first item will be
        # either '' or not preceded by \x01
        if len(items[0]) > 0:
            self.insert_with_tags(self.get_end_iter(), items[0], indent_tag)
            stripped_items.append(items[0])
        for item in items[1:]:
            if item.startswith('('):
                pos = item.find(')')
                if pos >= 2:
                    action = item[1]
                    code = item[2:pos]
                    if action == '+':
                        # set attribute
                        attr_list.append(self.attr_tag[code[0]])
                    elif action == '-':
                        if self.attr_tag[code[0]] in attr_list:
                            attr_list.remove(self.attr_tag[code[0]])
                    else:
                        # reset attributes and color
                        if code == 'r':
                            color_tag = self.create_tag()
                            attr_list = []
                        else:
                            # set attributes + color
                            while code.startswith(('*', '!', '/', '_', '|',
                                                   'r')):
                                if code[0] == 'r':
                                    color_tag = self.create_tag()
                                    attr_list = []
                                elif code[0] in self.attr_tag:
                                    attr_list.append(self.attr_tag[code[0]])
                                code = code[1:]
                            if code:
                                if action == "F":
                                    if code != "$":
                                        rgba = Gdk.RGBA()
                                        rgba.parse(code)
                                        color_tag = self.create_tag(
                                            foreground_rgba=rgba)
                                elif action == "B":
                                    if code != "$":
                                        rgba = Gdk.RGBA()
                                        rgba.parse(code)
                                        color_tag.props.background_rgba = rgba
                    item = item[pos+1:]
            if len(item) > 0:
                self.insert_with_tags(
                    self.get_end_iter(), item, color_tag, *attr_list, indent_tag)
                stripped_items.append(item)
        if indent == "prefix":
            text = ''.join(stripped_items)
            width = self.get_text_pixel_width(
                text, True if self.attr_tag["*"] in attr_list else False)
            indent_tag.props.indent = -width
            indent_tag.props.left_margin = self.longest_prefix - \
                width+int(self.config.get('look', 'margin_size'))
            if self.last_message_type != MessageType.TIME_STAMP and (msg_type == MessageType.CHAT_MESSAGE or msg_type != self.last_message_type):
                indent_tag.props.pixels_above_lines = 10
        elif indent == "no_prefix":
            indent_tag.props.left_margin = self.longest_prefix + \
                int(self.config.get('look', 'margin_size'))
        if indent in ("no_prefix", "text"):
            stripped_items = ''.join(stripped_items)
            for url_match in URL_PATTERN.finditer(stripped_items):
                span = url_match.span()
                start = self.get_end_iter()
                start.backward_chars(len(stripped_items)-span[0])
                end = self.get_end_iter()
                end.backward_chars(len(stripped_items)-span[1])
                tag = self.create_tag()
                tag.connect("event", self.on_url_clicked, url_match[0])
                self.apply_tag(tag, start, end)
                self.apply_tag(self.url_tag, start, end)

    def on_url_clicked(self, tag, source_object, event, text_iter, arg):
        if not event.type == Gdk.EventType.BUTTON_PRESS:
            return
        if not event.button.button == 1:
            return
        Gtk.show_uri_on_window(None, arg, Gdk.CURRENT_TIME)

    def get_text_pixel_width(self, text, bold=False):
        self.layout.set_text(text, -1)
        self.layout.set_attributes(None)
        if bold:
            # workaround to get an attribute list in pygobject:
            attr_list = Pango.parse_markup("<b>"+text+"</b>", -1, "0")[1]
            self.layout.set_attributes(attr_list)
        (width, _) = self.layout.get_pixel_size()
        if width > self.longest_prefix:
            for tag in self.indent_tag_list:
                tag.props.left_margin += width-self.longest_prefix
            self.longest_prefix = width
        return width

    def get_message_type(self, tags_array):
        if "irc_privmsg" in tags_array:
            return MessageType.CHAT_MESSAGE
        else:
            return MessageType.SERVER_MESSAGE


class BufferWidget(Gtk.Box):
    def __init__(self, config):
        Gtk.Box.__init__(self)
        self.config = config
        self.set_orientation(Gtk.Orientation.VERTICAL)
        horizontal_box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        self.pack_start(horizontal_box, True, True, 0)
        self.active = False

        # Scrolling:
        self.autoscroll = True

        # TextView widget
        self.textview = Gtk.TextView()
        self.scrolledwindow = Gtk.ScrolledWindow()
        self.scrolledwindow.set_hexpand(True)
        self.scrolledwindow.set_vexpand(True)
        # self.scrolledwindow.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.ALWAYS)
        self.scrolledwindow.connect("scroll-event", self.on_scroll_event)
        self.scrolledwindow.connect("scroll-child", self.on_scroll_child)
        self.scrolledwindow.connect("edge-reached", self.on_edge_reached)
        vscroll = self.scrolledwindow.get_vscrollbar()
        vscroll.connect("change-value", self.on_changed_value)
        self.textview.connect("size-allocate", self.on_size_allocate)
        self.textview.set_cursor_visible(False)
        self.textview.set_editable(False)
        self.textview.set_can_focus(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_right_margin(int(self.config.get('look',
                                                           'margin_size')))
        self.scrolledwindow.add(self.textview)
        horizontal_box.pack_start(self.scrolledwindow, True, True, 0)
        self.adjustment = self.textview.get_vadjustment()
        self.textview.connect("event", self.on_event)

        # Entry widget
        self.entry = Gtk.Entry()
        self.entry.connect("key-press-event", self.on_key_press)
        self.pack_start(self.entry, False, False, 0)
        self.completions = None
        self.completions_word_offset = None

        # Nicklist widget
        nicklist_renderer = Gtk.CellRendererText()
        nicklist_column = Gtk.TreeViewColumn("", nicklist_renderer, text=0)
        self.nick_display_widget = Gtk.TreeView()
        self.nick_display_widget.set_headers_visible(False)
        self.nick_display_widget.set_can_focus(False)
        self.nick_display_widget.append_column(nicklist_column)
        self.nick_display_widget.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.nicklist_window = Gtk.ScrolledWindow()
        self.nicklist_window.set_propagate_natural_width(True)
        self.nicklist_window.add(self.nick_display_widget)
        sep = Gtk.Separator()
        horizontal_box.pack_start(sep, False, False, 0)
        horizontal_box.pack_start(self.nicklist_window, False, False, 0)

        # Mouse cursors
        self.pointer_cursor = Gdk.Cursor.new_from_name(
            Gdk.Display.get_default(), "pointer")
        self.text_cursor = Gdk.Cursor.new_from_name(
            Gdk.Display.get_default(), "text")

    def on_event(self, source, event):
        """ Handler for mouse movement events. """
        if event.type != Gdk.EventType.MOTION_NOTIFY:
            return False
        win = self.textview.get_window(Gtk.TextWindowType.TEXT)
        coords = self.textview.window_to_buffer_coords(
            Gtk.TextWindowType.TEXT, event.x, event.y)
        text_iter = self.textview.get_iter_at_location(*coords)
        if text_iter[0] and text_iter[1].has_tag(self.get_url_tag()):
            win.set_cursor(self.pointer_cursor)
        else:
            win.set_cursor(self.text_cursor)

    def on_key_press(self, source_widget, event):
        if event.keyval == Gdk.KEY_Tab:
            text = self.entry.get_text()
            cursor_pos = self.entry.props.cursor_position
            text = text[:cursor_pos]
            word_pos = text.rfind(
                ' ')+1 if self.completions_word_offset is None else self.completions_word_offset
            self.completions_word_offset = word_pos
            if cursor_pos == word_pos:
                return True
            text = text[word_pos:]
            text = text.lower()
            if self.completions is None:
                self.completions = []
                model = self.nick_display_widget.get_model()
                for nick in model:
                    if nick[0].lower().find(text) == 1:
                        self.completions.append(nick[0][1:])
            if self.completions == []:
                self.completions = None
                return True
            match = self.completions.pop(0)
            self.completions.append(match)
            buf = self.entry.get_buffer()
            buf.delete_text(word_pos, cursor_pos-word_pos)
            if word_pos == 0:
                match += ": "
            buf.insert_text(word_pos, match, -1)
            self.entry.emit(
                "move-cursor", Gtk.MovementStep.VISUAL_POSITIONS, len(match), False)
            return True
        else:
            self.completions = None
            self.completions_word_offset = None
            return False

    def on_edge_reached(self, source_widget, pos):
        """This callback gets called when chat is scrolled to top/bottom."""
       # if not self.active:
       #     return
        if pos == Gtk.PositionType.BOTTOM:
            adj = self.scrolledwindow.get_vadjustment()
            if adj.get_value()+adj.get_page_size() >= adj.get_upper():
                self.autoscroll = True

    def on_changed_value(self, source, scroll, value):
        """This function is called when the scrollbar is dragged up/down."""
        if scroll in (Gtk.ScrollType.START, Gtk.ScrollType.PAGE_UP,
                      Gtk.ScrollType.STEP_UP, Gtk.ScrollType.JUMP):
            adj = self.scrolledwindow.get_vadjustment()
            if adj.get_value()+adj.get_page_size() < adj.get_upper():
                self.autoscroll = False

    def on_size_allocate(self, source_widget, allocation):
        """Callback for Gtk.Widget size-allocate signal.
        Needed to fix autoscroll that in some situations
        seemed to jump to bottom before widget had finished
        rendering, causing autoscroll to malfunction."""
        self.scrollbottom()

    def on_scroll_child(self, source_event, scroll, horizontal):
        """This callback is called when scrolling with up/down/pgup/pgdown."""
        if scroll in (Gtk.ScrollType.STEP_BACKWARD,
                      Gtk.ScrollType.START, Gtk.ScrollType.PAGE_BACKWARD):
            self.autoscroll = False

    def on_scroll_event(self, source_object, event):
        """This callback is called when scrolling with mousewheel."""
        if event.direction == Gdk.ScrollDirection.UP:
            self.autoscroll = False
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < 0:
                self.autoscroll = False

    def scrollbottom(self):
        """Scrolls to bottom if autoscroll is True."""
        if not self.active:
            return
        if not self.autoscroll:
            return
        # Make sure widget is properly updated before trying to scroll it:
        while Gtk.events_pending():
            Gtk.main_iteration()
        adj = self.scrolledwindow.get_vadjustment()
        adj.set_value(adj.get_upper()-adj.get_page_size())

    def get_url_tag(self):
        """Give us the Textview tag for URL:s. Must be implemented by the Buffer class."""
        raise NotImplementedError()


class Buffer(BufferWidget):
    """A WeeChat buffer that holds buffer data."""
    __gsignals__ = {
        'messageToWeechat': (GObject.SIGNAL_RUN_LAST, None,
                             (Gtk.Widget,)),
        'notifyLevelChanged': (GObject.SIGNAL_RUN_LAST, None,
                               tuple())
    }

    def __init__(self, config, data={}):
        BufferWidget.__init__(self, config)
        self.data = data
        self.nicklist = {}
        self.entry.connect("activate", self.on_send_message)
        self.nicklist_data = Gtk.ListStore(str)
        self.chat = ChatTextBuffer(
            config, layout=self.textview.create_pango_layout())
        self.textview.set_buffer(self.chat)
        self.nick_display_widget.set_model(self.nicklist_data)
        green = Gdk.RGBA(0, 0.7, 0, 1)
        orange = Gdk.RGBA(1, 0.5, 0.2, 1)
        blue = Gdk.RGBA(0.2, 0.2, 0.7, 1)
        self.colors_for_notify = {"default": self.get_theme_fg_color(
        ), "mention": green, "message": orange, "low": blue}
        self.notify_values = {"default": 0,
                              "low": 1, "message": 2, "mention": 3}
        self.notify_level = "default"

    def get_url_tag(self):
        return self.chat.url_tag

    def get_theme_fg_color(self):
        styleContext = self.get_style_context()
        (color_is_defined, theme_fg_color) = styleContext.lookup_color("theme_fg_color")
        return theme_fg_color if color_is_defined else Gdk.RGBA(0, 0, 0, 1)

    def update_buffer_default_color(self):
        if self.colors_for_notify:
            self.colors_for_notify["default"] = self.get_theme_fg_color()

    def nicklist_add_item(self, parent, group, prefix, name, visible):
        """Add a group/nick in nicklist."""
        if group:
            self.nicklist[name] = {
                'visible': visible,
                'nicks': []
            }
        else:
            self.nicklist[parent]['nicks'].append({
                'prefix': prefix,
                'name': name,
                'visible': visible,
            })

    def nicklist_refresh(self):
        """Refresh nicklist."""
        self.nicklist_data.clear()
        for group in sorted(self.nicklist):
            for nick in sorted(self.nicklist[group]['nicks'],
                               key=lambda n: n['name'].lower()):
                self.nicklist_data.append((nick["prefix"] + nick['name'],))
        if len(self.nicklist_data) > 0:
            if not self.nicklist_window.get_visible():
                self.nicklist_window.show_all()
              #  prefix_color = {
              #      '': '',
              #      ' ': '',
              #      '+': 'yellow',
              #  }
                #color = prefix_color.get(nick['prefix'], 'green')
                # if color:
                #    icon = QtGui.QIcon(
                #       resource_filename(__name__,
                #                         'data/icons/bullet_%s_8x8.png' %
                #                         color))
               # else:
                #  pixmap = QtGui.QPixmap(8, 8)
                # pixmap.fill()
                # icon = QtGui.QIcon(pixmap)
                #item = QtGui.QListWidgetItem(icon, nick['name'])
                # self.widget.nicklist.addItem(item)
        # self.widget.nicklist.setVisible(True)

    def nicklist_remove_item(self, parent, group, name):
        """Remove a group/nick from nicklist."""
        if group:
            if name in self.nicklist:
                del self.nicklist[name]
        else:
            if parent in self.nicklist:
                self.nicklist[parent]['nicks'] = [
                    nick for nick in self.nicklist[parent]['nicks']
                    if nick['name'] != name
                ]

    def nicklist_update_item(self, parent, group, prefix, name, visible):
        """Update a group/nick in nicklist."""
        if group:
            if name in self.nicklist:
                self.nicklist[name]['visible'] = visible
        else:
            if parent in self.nicklist:
                for nick in self.nicklist[parent]['nicks']:
                    if nick['name'] == name:
                        nick['prefix'] = prefix
                        nick['visible'] = visible
                        break

    def on_send_message(self, source_object):
        self.emit("messageToWeechat", source_object)

    def get_notify_color(self):
        return self.colors_for_notify[self.notify_level]

    def set_notify_level(self, notify_level):
        if self.notify_values[notify_level] > self.notify_values[self.notify_level]:
            self.notify_level = notify_level
            self.emit("notifyLevelChanged")

    def reset_notify_level(self):
        self.notify_level = "default"
        self.emit("notifyLevelChanged")

    def get_name(self):
        name = self.data["short_name"]
        if name is None:
            name = self.data["full_name"]
        return name

    def get_topic(self):
        return self.data["title"]

    def pointer(self):
        """Return pointer on buffer."""
        return self.data.get("__path", [""])[0]

    def clear(self):
        self.chat.delete(*self.chat.get_bounds())
