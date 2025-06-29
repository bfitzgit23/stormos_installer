#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import os
import subprocess
import getpass
import tempfile
import stat

# === EMBEDDED STYLES ===
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

# === CNCHI CONFIGURATION ===
CNCHI_CONFIG = """[SETTINGS]
desktop=XFCE
auto_mirror=true
enable_firewall=true
install_recommends=true
no_check=false
theme=default
"""

# === SYSTEMD SERVICE ===
SYSTEMD_SERVICE = """
[Unit]
Description=StormOS Installer GUI
After=graphical.target

[Service]
Type=simple
ExecStart=/usr/bin/stormos-installer
Restart=never
User=%I
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/%I/.Xauthority"

[Install]
WantedBy=graphical.target
"""

# === DESKTOP ENTRY ===
DESKTOP_ENTRY = """
[Desktop Entry]
Name=StormOS Installer
Exec=stormos_installer
Icon=system-software-install
Terminal=false
Type=Application
Categories=System;Utility;
"""

# === PKGBUILD TEMPLATE ===
PKGBUILD_TEMPLATE = """
# Maintainer: StormOS-Dev linuxstormos@gmail.com
pkgname=stormos_installer
pkgver=1.0
pkgrel=1
pkgdesc="Custom GTK 3.0 installer for StormOS with light/dark mode"
arch=('any')
url="https://github.com/bfitzgit23/stormos_installer "
license=('GPL3')
depends=('python' 'python-gobject' 'gtk3' 'cnchi')
source=("stormos-installer.py")
sha256sums=('SKIP')

package() {{
    install -Dm755 "$srcdir/stormos-installer.py" "$pkgdir/usr/bin/stormos-installer"
}}
"""

class StormOSInstaller(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="StormOS Installer")
        self.set_border_width(10)
        self.set_default_size(500, 300)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.apply_css(LIGHT_STYLE)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        label = Gtk.Label()
        label.set_markup("<big>Welcome to <b>StormOS Installer</b></big>")
        vbox.pack_start(label, True, True, 0)

        # Dark mode toggle
        self.mode_switch = Gtk.Switch()
        self.mode_switch.connect("notify::active", self.on_mode_toggled)
        hbox = Gtk.Box(spacing=6)
        hbox.pack_start(Gtk.Label(label="Dark Mode"), False, False, 0)
        hbox.pack_start(self.mode_switch, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)

        # Generate files button
        gen_button = Gtk.Button(label="Generate Service/Desktop/PKGBUILD")
        gen_button.connect("clicked", self.on_generate_clicked)
        vbox.pack_start(gen_button, False, False, 0)

        # Install Button
        install_button = Gtk.Button(label="Start Installation (CNCHI)")
        install_button.connect("clicked", self.on_install_clicked)
        vbox.pack_start(install_button, False, False, 0)

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

    def write_file(self, path, content, executable=False):
        try:
            with open(path, "w") as f:
                f.write(content)
            if executable:
                os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            print(f"[+] Wrote: {path}")
        except Exception as e:
            print(f"[!] Failed to write {path}: {e}")

    def write_cnchi_config(self):
        cnchi_dir = "/etc/cnchi"
        config_path = f"{cnchi_dir}/cnchi.conf"

        if not os.path.exists(cnchi_dir):
            os.makedirs(cnchi_dir)

        if not os.path.exists(config_path):
            try:
                with open(config_path, "w") as f:
                    f.write(CNCHI_CONFIG)
                print("[+] CNCHI config written.")
            except PermissionError:
                print("[!] Could not write CNCHI config: Permission denied")

    def on_generate_clicked(self, widget):
        home = os.path.expanduser("~")
        output_dir = os.path.join(home, "stormos-installer-output")
        os.makedirs(output_dir, exist_ok=True)

        # Write systemd service
        self.write_file(os.path.join(output_dir, "stormos-installer.service"), SYSTEMD_SERVICE)

        # Write desktop entry
        self.write_file(os.path.join(output_dir, "stormos-installer.desktop"), DESKTOP_ENTRY)

        # Write PKGBUILD
        self.write_file(os.path.join(output_dir, "PKGBUILD"), PKGBUILD_TEMPLATE)

        # Write this script itself
        script_path = os.path.join(output_dir, "stormos-installer.py")
        with open(__file__, "r") as src:
            script_content = src.read()
        self.write_file(script_path, script_content, executable=True)

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Files Generated",
        )
        dialog.format_secondary_text(f"Saved to: {output_dir}")
        dialog.run()
        dialog.destroy()

    def on_install_clicked(self, widget):
        self.write_cnchi_config()
        try:
            subprocess.Popen(["cnchi"])
            Gtk.main_quit()
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error launching CNCHI",
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()


def main():
    win = StormOSInstaller()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
