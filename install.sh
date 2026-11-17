#!/bin/sh
# ENVY SkyWatch — Linux installer (no root required).
#
# Downloads the latest release's linux-x86_64 bundle, verifies it against the
# release's SHA256SUMS, and installs it under ~/.local with a menu entry.
#
#   curl -fsSL https://raw.githubusercontent.com/xzchick/envy-skywatch/main/install.sh | sh
#
# Env overrides:
#   ENVY_INSTALL_TAG=vX.Y.Z              install a specific release
#   ENVY_INSTALL_SKIP_PLATFORM_CHECK=1   bypass the Linux/x86_64 guard (advanced)
set -eu

OWNER="xzchick"
REPO="envy-skywatch"
BUNDLE="envy-skywatch"
NAME="ENVY SkyWatch"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

if [ "${ENVY_INSTALL_SKIP_PLATFORM_CHECK:-0}" != "1" ]; then
  [ "$(uname -s)" = "Linux" ] || die "this installer is for Linux; on macOS use: brew install --cask $BUNDLE"
  case "$(uname -m)" in
    x86_64|amd64) : ;;
    *) die "only x86_64 Linux bundles are published (got $(uname -m)); build from source instead" ;;
  esac
fi

have tar || die "need tar"
have curl || have wget || die "need curl or wget"
fetch() { if have curl; then curl -fsSL "$1" -o "$2"; else wget -qO "$2" "$1"; fi; }
fetch_out() { if have curl; then curl -fsSL "$1"; else wget -qO- "$1"; fi; }

say "Resolving latest release of $OWNER/$REPO..."
TAG="${ENVY_INSTALL_TAG:-}"
if [ -z "$TAG" ]; then
  TAG=$(fetch_out "https://api.github.com/repos/$OWNER/$REPO/releases/latest" \
        | sed -n 's/.*"tag_name"[ ]*:[ ]*"\([^"]*\)".*/\1/p' | head -n1)
fi
[ -n "$TAG" ] || die "could not determine the latest release tag"
say "Latest: $TAG"

ASSET="$BUNDLE-$TAG-linux-x86_64.tar.gz"
URLBASE="https://github.com/$OWNER/$REPO/releases/download/$TAG"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT INT TERM
cd "$TMP"

say "Downloading $ASSET..."
fetch "$URLBASE/$ASSET" "$ASSET"
fetch "$URLBASE/SHA256SUMS.txt" "SHA256SUMS.txt"

awk -v a="$ASSET" '$2==a{print}' SHA256SUMS.txt > sums.asset
[ -s sums.asset ] || die "no checksum for $ASSET in SHA256SUMS.txt"
say "Verifying checksum..."
if have sha256sum; then sha256sum -c sums.asset >/dev/null
elif have shasum; then shasum -a 256 -c sums.asset >/dev/null
else die "need sha256sum or shasum to verify the download"; fi
say "Checksum OK."
if have cosign; then
  say "(tip) verify the Sigstore signature too:"
  say "   cosign verify-blob --certificate-identity-regexp 'https://github.com/$OWNER/$REPO/.github/workflows/release.yml@.*' --certificate-oidc-issuer https://token.actions.githubusercontent.com --bundle $URLBASE/SHA256SUMS.txt.sigstore.json SHA256SUMS.txt"
fi

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
LIBDIR="$DATA/envy"; BINDIR="$HOME/.local/bin"; APPDIR="$DATA/applications"
mkdir -p "$LIBDIR" "$BINDIR" "$APPDIR"

say "Installing..."
tar -xzf "$ASSET" -C "$LIBDIR"
DEST="$LIBDIR/$BUNDLE-$TAG-linux-x86_64"
[ -e "$DEST/$BUNDLE" ] || die "binary '$BUNDLE' not found inside the bundle"
chmod +x "$DEST/$BUNDLE" 2>/dev/null || true

for d in "$LIBDIR/$BUNDLE-"*"-linux-x86_64"; do
  [ "$d" = "$DEST" ] && continue
  [ -d "$d" ] && rm -rf "$d"
done

ln -sf "$DEST/$BUNDLE" "$BINDIR/$BUNDLE"
cat > "$APPDIR/$BUNDLE.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$NAME
Comment=$NAME (ENVY BLACK VEIL)
Exec=$DEST/$BUNDLE
Terminal=false
Categories=Utility;Security;
EOF

say ""
say "Installed $NAME $TAG"
say "  binary : $BINDIR/$BUNDLE"
say "  bundle : $DEST"
say "  launcher: $APPDIR/$BUNDLE.desktop"
case ":$PATH:" in
  *":$BINDIR:"*) say "Run it:  $BUNDLE" ;;
  *) say ""; say "NOTE: $BINDIR is not on your PATH yet. Add to your shell rc:"
     say '   export PATH="$HOME/.local/bin:$PATH"'
     say "then run: $BUNDLE" ;;
esac
say ""
say "Uninstall: rm -rf \"$DEST\" \"$BINDIR/$BUNDLE\" \"$APPDIR/$BUNDLE.desktop\""
