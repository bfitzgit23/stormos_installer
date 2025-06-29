# Maintainer: Your Name <your@email.com>
pkgname=stormos-installer
pkgver=1.0
pkgrel=1
pkgdesc="StormOS Installer – Custom GTK 3.0 installer that copies ISO to disk"
arch=('any')
url="https://github.com/bfitzgit23/stormos_installer"
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
)
makedepends=('git')
source=("stormos-installer::git+https://github.com/bfitzgit23/stormos_installer.git")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/stormos-installer"
  git describe --tags | sed 's/-/./g' || git log -1 --format=%cd --date=short | sed 's/-//g'
}

build() {
  cd "$srcdir/stormos-installer"
  echo "Build step complete (no actual build needed)"
}

package() {
  cd "$srcdir/stormos-installer"

  # Install main script
  install -Dm755 stormos-installer.py "$pkgdir/usr/bin/stormos-installer"
  chmod +x "$pkgdir/usr/bin/stormos-installer"

  # Install desktop file
  install -Dm644 stormos-installer.desktop "$pkgdir/usr/share/applications/stormos-installer.desktop"

  # Install icon (if exists)
  if [ -f "assets/stormos-logo.png" ]; then
    install -d "$pkgdir/usr/share/icons/hicolor/256x256/apps/"
    cp assets/stormos-logo.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/stormos-installer.png"
  fi

  # Install systemd service (optional)
  if [ -f "stormos-installer.service" ]; then
    install -Dm644 stormos-installer.service "$pkgdir/usr/lib/systemd/user/stormos-installer.service"
  fi
}
