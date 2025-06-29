import os
import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import configparser
import shutil

APP_NAME = "StormOS Installer"

class StormOSInstaller(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=APP_NAME)
        self.set_default_size(600, 400)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.apply_css(DARK_STYLE)

        self.target_drive = None

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        label = Gtk.Label()
        label.set_markup("<big>Welcome to <b>StormOS Installer</b></big>")
        vbox.pack_start(label, True, True, 0)

        self.drive_combo = Gtk.ComboBoxText()
        self.refresh_drives()

        refresh_button = Gtk.Button(label="Refresh Drives")
        refresh_button.connect("clicked", lambda _: self.refresh_drives())

        drive_box = Gtk.Box(spacing=6)
        drive_box.pack_start(self.drive_combo, True, True, 0)
        drive_box.pack_start(refresh_button, False, False, 0)
        vbox.pack_start(drive_box, False, False, 0)

        install_button = Gtk.Button(label="Start Installation")
        install_button.connect("clicked", self.on_install_clicked)
        vbox.pack_start(install_button, False, False, 0)

    def apply_css(self, css_data):
        provider = Gtk.CssProvider()
        bytes_data = css_data.encode()
        provider.load_from_data(GLib.Bytes.new(bytes_data))
        screen = Gdk.Screen.get_default()
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def refresh_drives(self, widget=None):
        self.drive_combo.remove_all()
        try:
            output = subprocess.check_output(["lsblk", "-d", "-o", "NAME,SIZE,MODEL"], text=True)
            lines = output.strip().split('\n')[1:]  # Skip header
            for line in lines:
                parts = line.split()
                name = parts[0]
                size = parts[1]
                model = ' '.join(parts[2:])
                self.drive_combo.append_text(f"/dev/{name} - {size} - {model}")
        except Exception as e:
            print("Error reading drives:", e)

    def do_iso_to_disk_copy(self, device):
        print(f"[+] Using device: {device}")

        # Read config
        config = configparser.ConfigParser()
        config.read("/etc/stormos-installer/settings.conf")
        desktop = config["installer"]["desktop"]

        print(f"[+] Installing {desktop} system...")

        # Load modules
        module_dir = "/etc/stormos-installer/modules/"
        modules = sorted(os.listdir(module_dir))

        for mod in modules:
            if mod.endswith(".conf"):
                print(f"[+] Running module: {mod}")
                # You can parse each .conf file here
            elif mod.endswith(".sh"):
                print(f"[+] Running script: {mod}")
                subprocess.run([os.path.join(module_dir, mod)], check=True)

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Installation Complete",
        )
        dialog.format_secondary_text("Your system has been installed. Reboot now.")
        dialog.run()
        dialog.destroy()

    def on_install_clicked(self, widget):
        selected = self.drive_combo.get_active_text()
        if not selected:
            dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK, text="No Drive Selected")
            dialog.format_secondary_text("Please select a target drive before installing.")
            dialog.run()
            dialog.destroy()
            return

        device = selected.split()[0]  # Extract /dev/sda from combo box

        confirm_dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Installation",
        )
        confirm_dialog.format_secondary_text(f"This will erase {device} and copy all files from this ISO to the drive.\nAre you sure you want to continue?")
        response = confirm_dialog.run()
        confirm_dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.do_iso_to_disk_copy(device)


def main():
    win = StormOSInstaller()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
