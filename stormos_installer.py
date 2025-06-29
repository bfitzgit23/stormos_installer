#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import os
import sys
import subprocess
import stat
import shutil
import tempfile
import getpass

APP_NAME = "StormOS Installer"
INSTALL_DIR = "/etc/stormos-installer"
MODULES_DIR = f"{INSTALL_DIR}/modules"

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
        self.set_default_size(500, 300)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.apply_css(DARK_STYLE)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        label = Gtk.Label()
        label.set_markup("<big>Welcome to <b>StormOS Installer</b></big>")
        vbox.pack_start(label, True, True, 0)

        # Install Button
        install_button = Gtk.Button(label="Start Installation (Copy ISO to Disk)")
        install_button.connect("clicked", self.on_install_clicked)
        vbox.pack_start(install_button, False, False, 0)

    def apply_css(self, css_data):
        provider = Gtk.CssProvider()
        bytes_data = css_data.encode()
        provider.load_from_data(GLib.Bytes.new(bytes_data))
        screen = Gdk.Screen.get_default()
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def on_install_clicked(self, widget):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Installation",
        )
        dialog.format_secondary_text("This will erase /dev/sda and copy all files from this ISO to the target system.\nAre you sure you want to continue?")
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            return

        try:
            self.do_iso_to_disk_copy()
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Installation Failed",
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
            Gtk.main_quit()

    def do_iso_to_disk_copy(self):
        # Step 1: Wipe and partition /dev/sda
        print("[+] Partitioning /dev/sda...")
        subprocess.check_call(["sgdisk", "--zap-all", "/dev/sda"])
        subprocess.check_call(["sgdisk", "--new", "1:0:+512M", "--typecode=1:ef00", "--change-name=1:'EFI System'", "/dev/sda"])
        subprocess.check_call(["sgdisk", "--new", "2:0:0", "--typecode=2:8300", "--change-name=2:'Linux Root'", "/dev/sda"])

        # Step 2: Format partitions
        print("[+] Formatting EFI and root partitions...")
        subprocess.check_call(["mkfs.fat", "-F32", "/dev/sda1"])
        subprocess.check_call(["mkfs.ext4", "/dev/sda2"])

        # Step 3: Mount them
        print("[+] Mounting partitions...")
        os.makedirs("/mnt", exist_ok=True)
        subprocess.check_call(["mount", "/dev/sda2", "/mnt"])
        os.makedirs("/mnt/boot", exist_ok=True)
        subprocess.check_call(["mount", "/dev/sda1", "/mnt/boot"])

        # Step 4: Copy all live ISO files to /mnt
        print("[+] Copying files from live ISO to /mnt...")

        exclude = ["/proc", "/sys", "/run", "/tmp", "/dev", "/boot", "/etc", "/var/cache/pacman/pkg"]

        for src_dir in ["/", "/boot", "/etc", "/usr", "/var"]:
            if os.path.exists(src_dir):
                print(f"[+] Copying {src_dir}...")
                shutil.copytree(
                    src_dir,
                    f"/mnt{src_dir}",
                    symlinks=True,
                    ignore=lambda src, names: [name for name in names if os.path.join(src, name) in exclude],
                    dirs_exist_ok=True
                )

        # Step 5: Write fstab
        print("[+] Generating fstab...")
        with open("/mnt/etc/fstab", "w") as f:
            f.write("UUID=$(blkid -s UUID -o value /dev/sda2)\necho UUID=\$UUID / ext4 defaults 0 1\n" +
                    "UUID=$(blkid -s UUID -o value /dev/sda1)\necho UUID=\$UUID /boot vfat defaults 0 2\n")
        subprocess.check_call(["genfstab", "-U", "/mnt", ">>", "/mnt/etc/fstab"], shell=True)

        # Step 6: Chroot setup
        print("[+] Setting up bootloader...")
        subprocess.check_call(["arch-chroot", "/mnt", "grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"])
        subprocess.check_call(["arch-chroot", "/mnt", "grub-mkconfig", "-o", "/boot/grub/grub.cfg"])

        # Step 7: Set hostname
        print("[+] Setting hostname...")
        with open("/mnt/etc/hostname", "w") as f:
            f.write("stormos\n")

        # Step 8: Enable services
        print("[+] Enabling services...")
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
        Gtk.main_quit()


def main():
    win = StormOSInstaller()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
