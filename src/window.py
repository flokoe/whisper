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

import uuid
from gettext import gettext as _
from pathlib import Path
from typing import Any, Optional

from gi.repository import Adw, GLib, Gst, Gtk

from .database_manager import DatabaseManager


@Gtk.Template(resource_path="/de/flokoe/Whisper/window.ui")
class WhisperWindow(Adw.ApplicationWindow):
    __gtype_name__ = "WhisperWindow"

    nav_view = Gtk.Template.Child()
    record = Gtk.Template.Child()
    stop = Gtk.Template.Child()
    discard = Gtk.Template.Child()

    # Database
    data_dir = Path(GLib.get_user_data_dir())
    db = DatabaseManager(data_dir / "whisper.db")
    db.migrations()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Set up the pipeline to None initially
        self.pipeline: Optional[Gst.Element] = None
        self.current_recording_path: Optional[Path] = None

        # Connect Record button click to handler
        self.record.connect("clicked", self._on_record_clicked)

        # Connect Stop and Discard buttons
        self.stop.connect("clicked", self._on_stop_clicked)
        self.discard.connect("clicked", self._on_discard_clicked)

        # Connect navigation view signals
        self.nav_view.connect("popped", self._on_nav_view_popped)

        # Connect to window closing signal to stop recording if active
        self.connect("close-request", self._on_close_request)

    def _create_recording_pipeline(self) -> None:
        """Create GStreamer pipeline for recording audio with Opus codec."""
        # Create a unique filename with UUID
        # Use XDG data directory for Flatpak compatibility
        recordings_dir = Path(GLib.get_user_data_dir()) / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)

        self.current_recording_path = recordings_dir / f"{uuid.uuid4()}.opus"

        # Print the recording path for debugging
        print(f"Recording to: {self.current_recording_path}")

        # Create GStreamer pipeline
        pipeline_str = (
            "autoaudiosrc ! audioconvert ! audioresample ! "
            "opusenc bitrate=24000 bitrate-type=1 complexity=10 frame-size=60 audio-type=2048 ! oggmux ! filesink location="
            + str(self.current_recording_path)
        )
        self.pipeline = Gst.parse_launch(pipeline_str)

    def _start_recording(self) -> None:
        """Start the audio recording."""
        if self.pipeline is None:
            self._create_recording_pipeline()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.PLAYING)

    def _pause_recording(self) -> None:
        """Pause the audio recording temporarily."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.PAUSED)

    def _resume_recording(self) -> None:
        """Resume a paused audio recording."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.PLAYING)

    def _stop_recording(self) -> None:
        """Stop the audio recording."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            if self.current_recording_path:
                print(f"Saved recording to: {self.current_recording_path}")

    def _discard_recording(self) -> None:
        """Discard the current recording by deleting the file."""
        self._stop_recording()

        if self.current_recording_path and self.current_recording_path.exists():
            print(f"Discarding recording: {self.current_recording_path}")
            self.current_recording_path.unlink()

        self.current_recording_path = None
        self.pipeline = None

    def _on_record_clicked(self, button: Gtk.Button) -> None:
        """Switch to recording page and start recording when Record button is clicked."""
        # Navigate to the recording page
        self.nav_view.push_by_tag("recording")
        # Start recording
        self._start_recording()

    def _on_stop_clicked(self, button: Gtk.Button) -> None:
        """Stop recording and return to home page when Stop button is clicked."""
        # Stop the recording
        self._stop_recording()
        # Clean up pipeline
        self.pipeline = None
        # Navigate back to the home page
        self.nav_view.pop()

    def _create_discard_confirmation_dialog(
        self,
        heading: str = _("Discard Recording?"),
        body: str = _(
            "Are you sure you want to discard this recording? This action cannot be undone."
        ),
        discard_label: str = _("Discard"),
        callback: Any = None,
        show_save: bool = False,
    ) -> Adw.MessageDialog:
        """Create a confirmation dialog for discarding recordings.

        Args:
            heading: Dialog title
            body: Dialog message
            discard_label: Label for the discard button
            callback: Function to call when dialog is responded to
            show_save: Whether to show a Save option (for navigation/close cases)

        Returns:
            The configured dialog
        """
        dialog = Adw.MessageDialog.new(self, heading, body)

        if show_save:
            dialog.add_response("save", _("Save"))
            dialog.add_response("discard", discard_label)
            dialog.set_default_response("save")
        else:
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("discard", discard_label)
            dialog.set_default_response("cancel")

        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)

        if callback:
            dialog.connect("response", callback)

        return dialog

    def _on_discard_clicked(self, button: Gtk.Button) -> None:
        """Discard recording and return to home page when Discard button is clicked."""
        # Pause the recording while dialog is shown
        self._pause_recording()

        dialog = self._create_discard_confirmation_dialog(
            callback=self._on_discard_dialog_response
        )
        dialog.present()

    def _on_discard_dialog_response(
        self, dialog: Adw.MessageDialog, response: str
    ) -> None:
        """Handle the response from the discard confirmation dialog."""
        if response == "discard":
            # Discard the recording
            self._discard_recording()
            # Navigate back to the home page
            self.nav_view.pop()
        else:
            # Resume recording if canceled
            self._resume_recording()

    def _on_nav_view_popped(
        self, nav_view: Gtk.Widget, page: Adw.NavigationPage
    ) -> bool:
        """Handle navigation back from recording page with option to save."""
        # Check if we're popping from the recording page
        if page.get_tag() == "recording" and self.pipeline is not None:
            # Pause the recording while dialog is shown
            self._pause_recording()

            dialog = self._create_discard_confirmation_dialog(
                heading=_("Save Recording?"),
                body=_("Do you want to save your current recording?"),
                discard_label=_("Discard"),
                callback=self._on_nav_view_dialog_response,
                show_save=True,
            )
            dialog.present()

            # Prevent navigation for now (will be handled in dialog response)
            return True
        return False

    def _on_nav_view_dialog_response(
        self, dialog: Adw.MessageDialog, response: str
    ) -> None:
        """Handle the response from the nav_view dialog."""
        if response == "discard":
            # Discard the recording
            self._discard_recording()
            # Now manually navigate back
            self.nav_view.pop()
        elif response == "save":
            # Stop and save the recording
            self._stop_recording()
            self.pipeline = None
            # Navigate back
            self.nav_view.pop()
        else:  # "cancel"
            # Resume recording if canceled
            self._resume_recording()

    def _on_close_request(self, window: Adw.ApplicationWindow) -> bool:
        """Handle window close request by stopping any active recording."""
        if self.pipeline is not None:
            # Pause the recording while dialog is shown
            self._pause_recording()

            dialog = self._create_discard_confirmation_dialog(
                heading=_("Save Recording?"),
                body=_("Do you want to save your recording before closing?"),
                discard_label=_("Discard and Close"),
                callback=self._on_close_dialog_response,
                show_save=True,
            )
            dialog.present()
            return True  # Prevent window from closing until user responds
        return False  # Allow window to close

    def _on_close_dialog_response(
        self, dialog: Adw.MessageDialog, response: str
    ) -> None:
        """Handle the response from the close confirmation dialog."""
        if response == "discard":
            # Discard the recording
            self._stop_recording()
            self.pipeline = None
            # Destroy window to close the app
            self.destroy()
        elif response == "save":
            # Save the recording
            self._stop_recording()
            self.pipeline = None
            # Destroy window to close the app
            self.destroy()
        else:  # "cancel"
            # Resume recording if canceled
            self._resume_recording()
