# window.py
#
# Copyright 2025 Florian
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any

from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/de/flokoe/Whisper/window.ui")
class WhisperWindow(Adw.ApplicationWindow):
    __gtype_name__ = "WhisperWindow"

    nav_view = Gtk.Template.Child()
    record = Gtk.Template.Child()
    stop = Gtk.Template.Child()
    discard = Gtk.Template.Child()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Connect Record button click to handler
        self.record.connect("clicked", self._on_record_clicked)

        # Connect Stop and Discard buttons
        self.stop.connect("clicked", self._on_stop_clicked)
        self.discard.connect("clicked", self._on_discard_clicked)

    def _on_record_clicked(self, button: Gtk.Button) -> None:
        """Switch to recording page when Record button is clicked."""
        # Navigate to the recording page
        self.nav_view.push_by_tag("recording")

    def _on_stop_clicked(self, button: Gtk.Button) -> None:
        """Return to home page when Stop button is clicked."""
        # Navigate back to the home page
        self.nav_view.pop()

    def _on_discard_clicked(self, button: Gtk.Button) -> None:
        """Return to home page when Discard button is clicked."""
        # Navigate back to the home page
        self.nav_view.pop()
