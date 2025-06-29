#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import os
import sys
import subprocess
import stat
import shutil
import configparser
import getpass

APP_NAME = "StormOS Installer"

# === DEFINE STYLES ===
LIGHT_STYLE = """
window {
    background-color: #f8f8f8;
    color: #000000;
}
button {
    background-color: #e0e0e0;
    color: black;
    padding: 10px;
}
"""

DARK_STYLE = """
window {
    background-color: #2e2e2e;
    color: #ffffff;
}
button {
    background-color: #444;
    color: white;
    padding: 10px;
}
"""

class StormOSInstaller(Gtk.Window):
    def __init__(self):
        if not Gtk.init_check()[0]:
            print("GTK init failed")
            sys.exit(1)

        Gtk.Window.__init__(self, title=APP_NAME)
        self.set_default_size(600, 400)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.target_drive = None

        # Apply dark mode by default
        self.apply_css(DARK_STYLE)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        label = Gtk.Label()
        label.set_markup("<big>Welcome to <b>StormOS Installer</b></big>")
        vbox.pack_start(label, True, True, 0)

        # Drive selection
        self.drive_combo = Gtk.ComboBoxText()
        self.refresh_drives_button = Gtk.Button(label="Refresh Drives")
        self.refresh_drives_button.connect("clicked", self.on_refresh_clicked)
        self.drive_combo.set_entry_text_column(0)

        drive_box = Gtk.Box(spacing=6)
        drive_box.pack_start(self.drive_combo, True, True, 0)
        drive_box.pack_start(self.refresh_drives_button, False, False, 0)
        vbox.pack_start(drive_box, False, False, 0)

        # Dark mode toggle (optional)
        self.mode_switch = Gtk.Switch()
        self.mode_switch.connect("notify::active", self.on_mode_toggled)
        hbox = Gtk.Box(spacing=6)
        hbox.pack_start(Gtk.Label(label="Dark Mode"), False, False, 0)
        hbox.pack_start(self.mode_switch, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)

        # Start Install Button
        install_button = Gtk.Button(label="Start Installation (Copy ISO to Disk)")
        install_button.connect("clicked", self.on_install_clicked)
        vbox.pack_start(install_button, False, False, 0)

        # Refresh drives initially
        self.on_refresh_clicked(None)

    def apply_css(self, css_data):
        provider = Gtk.CssProvider()
        bytes_data = css_data.encode()
        provider.load_from_data(GLib.Bytes.new(bytes_data))
        screen = Gdk.Screen.get_default()
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def on_mode_toggled(self, switch, gparam):
        dark_mode = switch.get_active()
        if dark_mode:
            self.apply_css(DARK_STYLE)
        else:
            self.apply_css(LIGHT_STYLE)

    def on_refresh_clicked(self, widget=None):
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
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error reading drives",
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()

    def do_iso_to_disk_copy(self, device):
        print(f"[+] Using device: {device}")

        # Wipe existing partitions
        subprocess.check_call(["sgdisk", "--zap-all", device])

        # Create EFI partition
        subprocess.check_call(["sgdisk", "--new", "1:0:+512M", "--typecode=1:ef00", "--change-name=1:'EFI System'", device])
        # Create root partition
        subprocess.check_call(["sgdisk", "--new", "2:0:0", "--typecode=2:8300", "--change-name=2:'Linux Root'", device])

        # Format partitions
        subprocess.check_call(["mkfs.fat", "-F32", f"{device}1"])
        subprocess.check_call(["mkfs.ext4", "-F", f"{device}2"])

        # Mount them
        os.makedirs("/mnt", exist_ok=True)
        subprocess.check_call(["mount", f"{device}2", "/mnt"])
        os.makedirs("/mnt/boot", exist_ok=True)
        subprocess.check_call(["mount", f"{device}1", "/mnt/boot"])

        # Copy files
        exclude = ["/proc", "/sys", "/run", "/tmp", "/dev", "/boot", "/var/cache/pacman/pkg"]

        for src_dir in ["/", "/boot", "/etc", "/usr", "/var"]:
            if os.path.exists(src_dir):
                print(f"[+] Copying {src_dir}...")
                shutil.copytree(
                    src_dir,
                    f"/mnt{src_dir}",
                    symlinks=True,
                    ignore=lambda s, names: [n for n in names if os.path.join(s, n) in exclude],
                    dirs_exist_ok=True
                )

        # Set hostname
        with open("/mnt/etc/hostname", "w") as f:
            f.write("stormos\n")

        # Setup bootloader
        subprocess.check_call(["arch-chroot", "/mnt", "grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"])
        subprocess.check_call(["arch-chroot", "/mnt", "grub-mkconfig", "-o", "/boot/grub/grub.cfg"])

        # Enable services
        subprocess.check_call(["arch-chroot", "/mnt", "systemctl", "enable", "NetworkManager.service"])

        print("[+] Installation complete!")

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Installation Complete",
        )
        dialog.format_secondary_text("Your system has been installed. You can now reboot.")
        dialog.run()
        dialog.destroy()

    def on_install_clicked(self, widget):
        selected = self.drive_combo.get_active_text()
        if not selected:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="No Drive Selected",
            )
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
