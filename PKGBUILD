# Maintainer: Your Name <your@email.com>
pkgname=stormos-installer
pkgver=20250715
pkgrel=1
pkgdesc="StormOS Installer – Modular, Offline, GTK 3.0"
arch=('any')
url="https://github.com/bfitzgit23/stormos_installer "
license=('GPL3')
depends=(
    'python'
    'python-gobject'
    'gtk3'
    'parted'
    'dosfstools'
    'mtools'
    'ntfs-3g'
    'grub'
    'efibootmgr'
    'arch-install-scripts'
    'networkmanager'
    'gocryptfs'
)
makedepends=('git')
source=("stormos-installer::git+https://github.com/bfitzgit23/stormos_installer.git ")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/stormos-installer"
  git log -1 --format=%cd --date=short | sed 's/-//g'
}

build() {
  cd "$srcdir/stormos-installer"
  echo "Build step complete (no actual build needed)"
}

package() {
  cd "$srcdir/stormos-installer"

  # Create directories
  install -d "$pkgdir/usr/bin"
  install -d "$pkgdir/usr/share/applications"
  install -d "$pkgdir/usr/share/icons/hicolor/256x256/apps"
  install -d "$pkgdir/etc/stormos-installer/modules"
  install -d "$pkgdir/usr/lib/systemd/user/"

  # Copy main installer script
  install -Dm755 stormos-installer.py "$pkgdir/usr/bin/stormos-installer"
  chmod +x "$pkgdir/usr/bin/stormos-installer"

  # Copy desktop entry
  if [ -f "stormos-installer.desktop" ]; then
    install -Dm644 stormos-installer.desktop "$pkgdir/usr/share/applications/stormos-installer.desktop"
  else
    echo "[+] Creating default desktop entry..."
    cat > "$pkgdir/usr/share/applications/stormos-installer.desktop" <<EOF
[Desktop Entry]
Name=StormOS Installer
Exec=stormos-installer
Icon=system-software-install
Terminal=false
Type=Application
Categories=System;Utility;
Comment=Copy live ISO to disk with dark mode UI
EOF
  fi

  # Optional: Copy icon
  if [ -f "assets/stormos-logo.png" ]; then
    cp assets/stormos-logo.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/stormos-installer.png"
  fi

  # Optional: systemd service
  if [ -f "stormos-installer.service" ]; then
    install -Dm644 stormos-installer.service "$pkgdir/usr/lib/systemd/user/stormos-installer.service"
  else
    cat > "$pkgdir/usr/lib/systemd/user/stormos-installer.service" <<EOF
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
EOF
  fi

  # Write sample module configs
  cat > "$pkgdir/etc/stormos-installer/settings.conf" <<EOF
[installer]
desktop=XFCE
timezone=America/New_York
keyboard_layout=us
language=en_US.UTF-8
hostname=stormos
EOF

  cat > "$pkgdir/etc/stormos-installer/modules/001-users.conf" <<EOF
[users]
username=storm
password=storm
autologin=true
sudoers_nopasswd=true
EOF

  cat > "$pkgdir/etc/stormos-installer/modules/002-partition.conf" <<EOF
[partition]
type=auto
bootloader_device=/dev/sda
format=true
mount_point=/mnt
swap=false
EOF

  cat > "$pkgdir/etc/stormos-installer/modules/003-packages.conf" <<EOF
[packages]
include=base linux linux-firmware xfce4 xfce4-goodies networkmanager
exclude=
EOF

  cat > "$pkgdir/etc/stormos-installer/modules/004-bootloader.conf" <<EOF
[bootloader]
type=grub
uefi=true
device=/dev/sda
id=GRUB
EOF

  cat > "$pkgdir/etc/stormos-installer/modules/postinstall.sh" <<'EOF'
#!/bin/bash
set -e

echo "Setting hostname..."
echo "stormos" > /mnt/etc/hostname

echo "Setting up timezone..."
ln -sf /usr/share/zoneinfo/America/New_York /mnt/etc/localtime
hwclock --systohc

echo "Enabling NetworkManager..."
arch-chroot /mnt systemctl enable NetworkManager.service

echo "Installation Complete!"
EOF
  chmod +x "$pkgdir/etc/stormos-installer/modules/postinstall.sh"
}
