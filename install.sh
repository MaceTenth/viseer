#!/bin/bash
set -e

# Resolve the directory this script lives in, regardless of where it's called from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Installing viseer from: $SCRIPT_DIR"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install the package into the venv
echo "Installing package..."
"$VENV_DIR/bin/pip" install -q -e "$SCRIPT_DIR"

# Detect current shell
CURRENT_SHELL="$(basename "$SHELL")"

# Add alias for posix shells (zsh, bash, ksh)
add_posix_alias() {
    local name="$1"
    local rc="$2"
    local bin="$VENV_DIR/bin/$name"
    local alias_line="alias $name='$bin'"

    if grep -qF "$alias_line" "$rc" 2>/dev/null; then
        echo "Alias '$name' already in $rc, skipping."
    else
        echo "$alias_line" >> "$rc"
        echo "Added alias '$name' to $rc"
    fi
}

# Add alias for fish shell
add_fish_alias() {
    local name="$1"
    local bin="$VENV_DIR/bin/$name"
    local fish_config="$HOME/.config/fish/config.fish"
    local alias_line="alias $name='$bin'"

    mkdir -p "$(dirname "$fish_config")"
    if grep -qF "$alias_line" "$fish_config" 2>/dev/null; then
        echo "Alias '$name' already in $fish_config, skipping."
    else
        echo "$alias_line" >> "$fish_config"
        echo "Added alias '$name' to $fish_config"
    fi
}

case "$CURRENT_SHELL" in
    zsh)
        SHELL_RC="$HOME/.zshrc"
        add_posix_alias viseer "$SHELL_RC"
        add_posix_alias viseer-fetch "$SHELL_RC"
        ;;
    bash)
        # macOS uses .bash_profile, Linux uses .bashrc
        if [ -f "$HOME/.bash_profile" ]; then
            SHELL_RC="$HOME/.bash_profile"
        else
            SHELL_RC="$HOME/.bashrc"
        fi
        add_posix_alias viseer "$SHELL_RC"
        add_posix_alias viseer-fetch "$SHELL_RC"
        ;;
    fish)
        SHELL_RC="$HOME/.config/fish/config.fish"
        add_fish_alias viseer
        add_fish_alias viseer-fetch
        ;;
    ksh)
        SHELL_RC="$HOME/.kshrc"
        add_posix_alias viseer "$SHELL_RC"
        add_posix_alias viseer-fetch "$SHELL_RC"
        ;;
    *)
        echo "⚠️  Shell '$CURRENT_SHELL' not recognized. Add these lines to your shell config manually:"
        echo "   alias viseer='$VENV_DIR/bin/viseer'"
        echo "   alias viseer-fetch='$VENV_DIR/bin/viseer-fetch'"
        exit 0
        ;;
esac

echo ""
echo "✅ Done!"

# If sourced, reload rc immediately; if executed, exec a fresh shell
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # shellcheck disable=SC1090
    source "$SHELL_RC"
    echo "Aliases are active in this terminal."
else
    echo "Reloading shell to apply aliases..."
    exec "$SHELL"
fi
