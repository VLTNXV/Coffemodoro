#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { printf "${GREEN}==> ${NC}%s\n" "$*"; }
warn() { printf "${YELLOW}warn:${NC} %s\n" "$*"; }
die()  { printf "${RED}error:${NC} %s\n" "$*" >&2; exit 1; }

[[ -f pyproject.toml && -d coffemodoro ]] \
    || die "Run this from the coffemodoro repo root."

PREFIX="${HOME}/.local"
APPDIR="${PREFIX}/share/applications"
ICONDIR="${PREFIX}/share/icons/hicolor/scalable/apps"

# ── System dependencies ───────────────────────────────────────────────────────
info "Installing system dependencies..."

if command -v apt-get &>/dev/null; then
    sudo apt-get install -y \
        python3-pip \
        python3-gi python3-gi-cairo \
        gir1.2-gtk-4.0 gir1.2-adw-1 \
        gir1.2-notify-0.7 \
        gir1.2-gstreamer-1.0 gstreamer1.0-plugins-good \
        gir1.2-rsvg-2.0
    sudo apt-get install -y gir1.2-ayatanaappindicator3-0.1 2>/dev/null \
        || warn "Tray icon unavailable (gir1.2-ayatanaappindicator3-0.1 not found — optional)"

elif command -v dnf &>/dev/null; then
    sudo dnf install -y \
        python3-pip \
        python3-gobject gtk4 libadwaita \
        libnotify gstreamer1-plugins-good \
        librsvg2
    sudo dnf install -y libayatana-appindicator-gtk3 2>/dev/null \
        || warn "Tray icon unavailable (libayatana-appindicator-gtk3 not found — optional)"

elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm --needed \
        python-pip \
        python-gobject gtk4 libadwaita \
        libnotify gstreamer gst-plugins-good \
        librsvg
    sudo pacman -S --noconfirm --needed libayatana-appindicator 2>/dev/null \
        || warn "Tray icon unavailable (libayatana-appindicator not found — optional)"

else
    warn "Unknown package manager. Please install manually:"
    warn "  PyGObject, GTK4, libadwaita, libnotify, gstreamer (with OGG support)"
    warn "  Tray support also requires: libayatana-appindicator (optional)"
fi

# ── Python package ────────────────────────────────────────────────────────────
info "Installing Coffemodoro..."
# Use python3 -m pip to ensure we install for the same Python that system
# packages (python3-gi etc.) are compiled for, not a different pip on PATH.
python3 -m pip install --user . 2>/dev/null || \
    python3 -m pip install --user --break-system-packages .

# ── Desktop integration ───────────────────────────────────────────────────────
info "Installing desktop file and icons..."
mkdir -p "$APPDIR" "$ICONDIR"

cp coffemodoro.desktop "$APPDIR/coffemodoro.desktop"
# Copy all bundled icons (custom + pinned Adwaita versions for cross-distro consistency)
cp coffemodoro/assets/icons/hicolor/scalable/apps/*.svg "$ICONDIR/"

update-desktop-database "$APPDIR" 2>/dev/null || true
gtk-update-icon-cache -f "${PREFIX}/share/icons/hicolor" 2>/dev/null || true

# ── PATH check ────────────────────────────────────────────────────────────────
if [[ ":${PATH}:" != *":${HOME}/.local/bin:"* ]]; then
    warn "~/.local/bin is not in your PATH."
    warn "Add this to your ~/.bashrc or ~/.zshrc:"
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

info "Done! Run: coffemodoro"
printf "       Or find it in your app launcher.\n"
