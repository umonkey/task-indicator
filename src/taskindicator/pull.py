# encoding=utf-8

from __future__ import print_function

import fcntl
import gobject
import gtk
import os
import pango
import subprocess
import sys


class ProcessRunner(gtk.Window):
    def __init__(self):
        super(ProcessRunner, self).__init__()
        self.setup_window()

        self.proc = None

    def setup_window(self):
        self.set_default_size(700, 400)
        self.set_title("Getting external tasks")
        self.set_border_width(4)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_icon_name("taskui")

        def make_text():
            self.tv = gtk.TextView()
            font = pango.FontDescription("monospace")
            self.tv.modify_font(font)

            scroll = gtk.ScrolledWindow()
            scroll.add(self.tv)

            return scroll

        def make_button():
            btn = gtk.Button("Close")
            btn.connect("activate", self.on_close_clicked)
            btn.set_sensitive(False)
            self.close_button = btn
            return btn

        vbox = gtk.VBox(homogeneous=False, spacing=4)
        self.add(vbox)

        ctl = make_text()
        vbox.pack_start(ctl)

        ctl = make_button()
        vbox.pack_start(ctl, expand=False, fill=False)

    def run_process(self, command):
        self.add_text("> %s\n" % " ".join(command))

        self.proc = subprocess.Popen(command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        def read(stream):
            fd = stream.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            try:
                return stream.read()
            except:
                return ""

        def update():
            out = read(self.proc.stdout)
            self.add_text(out)

            err = read(self.proc.stderr)
            self.add_text(err)

            still_running = self.proc.poll() is None
            if not still_running:
                self.close_button.set_sensitive(True)
            return still_running

        tm = gobject.timeout_add(100, update)
        print(tm)

    @classmethod
    def run(cls, command):
        runner = cls()
        runner.show_all()
        runner.run_process(command)

    def add_text(self, text):
        self.tv.get_buffer().insert_at_cursor(text)

    def on_close_clicked(self):
        self.destroy()
