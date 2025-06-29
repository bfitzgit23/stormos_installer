#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GObject

import os
import sys
import subprocess
import shutil
import tempfile
import stat
import configparser

APP_NAME = "StormOS Installer"

# === DARK MODE STYLE ===
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

        self.apply_css(DARK_STYLE)

        self.target_drive = None

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

        # Install Button
        install_button = Gtk.Button(label="Start Installation (Copy ISO to Disk)")
        install_button.connect("clicked", self.on_install_clicked)
        vbox.pack_start(install_button, False, False, 0)

        # Bottom Buttons: Reboot / Quit
        self.reboot_button = Gtk.Button(label="Reboot System")
        self.reboot_button.set_sensitive(False)
        self.reboot_button.connect("clicked", self.on_reboot_clicked)

        self.quit_button = Gtk.Button(label="Quit Installer")
        self.quit_button.connect("clicked", self.on_quit_clicked)

        button_box = Gtk.Box(spacing=6)
        button_box.pack_start(self.reboot_button, True, True, 0)
        button_box.pack_start(self.quit_button, True, True, 0)
        vbox.pack_start(button_box, False, False, 0)

        # Refresh drives initially
        self.on_refresh_clicked(None)

        # Create modular config files
        self.create_module_configs()

    def apply_css(self, css_data):
        provider = Gtk.CssProvider()
        bytes_data = css_data.encode('utf-8')  # Ensure UTF-8 encoding
        provider.load_from_data(bytes_data)   # Pass raw bytes
        screen = Gdk.Screen.get_default()
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def create_module_configs(self):
        module_dir = "/etc/stormos-installer/modules"
        os.makedirs(module_dir, exist_ok=True)

        # Sample users.conf
        user_conf = os.path.join(module_dir, "users.conf")
        if not os.path.exists(user_conf):
            with open(user_conf, "w") as f:
                f.write("[users]\nusername=storm\npassword=storm\nhostname=stormos\nautologin=true\nsudoers_nopasswd=true\n")

        # Sample partition.conf
        part_conf = os.path.join(module_dir, "partition.conf")
        if not os.path.exists(part_conf):
            with open(part_conf, "w") as f:
                f.write("[partition]\ntype=auto\nswap=false\nbootloader_device=/dev/sda\nformat=true\nmount_point=/mnt\n")

        # Sample postinstall.sh
        post_sh = os.path.join(module_dir, "postinstall.sh")
        if not os.path.exists(post_sh):
            with open(post_sh, "w") as f:
                f.write("#!/bin/bash\nset -e\n\necho 'Setting hostname...'\necho 'stormos' > /mnt/etc/hostname\nln -sf /usr/share/zoneinfo/Region/City /mnt/etc/localtime\nhwclock --systohc\n\n# Enable services\narch-chroot /mnt systemctl enable NetworkManager.service\n")
            os.chmod(post_sh, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH)

        print(f"[+] Created modular configs in {module_dir}")

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

        # Copy live ISO contents
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

        # Run postinstall.sh
        postinstall_script = "/etc/stormos-installer/modules/postinstall.sh"
        if os.path.exists(postinstall_script):
            print("[+] Running postinstall.sh...")
            subprocess.check_call(["bash", postinstall_script])

        print("[+] Installation complete!")
        self.reboot_button.set_sensitive(True)

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

    def on_reboot_clicked(self, widget):
        print("[+] Rebooting system...")
        subprocess.check_call(["reboot"])

    def on_quit_clicked(self, widget):
        print("[+] Exiting installer...")
        Gtk.main_quit()


def main():
    win = StormOSInstaller()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
