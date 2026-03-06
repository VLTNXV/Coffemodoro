#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { printf "${GREEN}==> ${NC}%s\n" "$*"; }
warn() { printf "${YELLOW}warn:${NC} %s\n" "$*"; }

info "Uninstalling Coffemodoro..."
python3 -m pip uninstall -y coffemodoro 2>/dev/null || \
    python3 -m pip uninstall -y --break-system-packages coffemodoro 2>/dev/null || \
    warn "pip uninstall failed or package was not installed via pip"

info "Removing desktop integration..."
rm -f "${HOME}/.local/share/applications/coffemodoro.desktop"
rm -f "${HOME}/.local/share/icons/hicolor/scalable/apps/coffemodoro-"*.svg

update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f "${HOME}/.local/share/icons/hicolor" 2>/dev/null || true

info "Done."
