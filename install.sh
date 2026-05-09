#!/usr/bin/env bash

set -e

echo "========================================="
echo "        BrSeqTB Installer"
echo "========================================="

# Detect pipeline root directory
PIPELINE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WRAPPER_SRC="$PIPELINE_DIR/bin/brseqtb"
LOCAL_BIN="$HOME/.local/bin"

echo ""
echo "Pipeline directory: $PIPELINE_DIR"

# --------------------------------------------------
# Checks
# --------------------------------------------------
if ! command -v nextflow &> /dev/null; then
    echo "[WARNING] Nextflow not found in PATH. You will need it to run the pipeline."
fi

if ! command -v java &> /dev/null; then
    echo "[WARNING] Java not found in PATH."
fi

chmod +x "$WRAPPER_SRC"

# --------------------------------------------------
# Installation Strategy: Symlink to ~/.local/bin
# --------------------------------------------------
# This is the cleanest way. Most modern distros include ~/.local/bin in PATH.
# It works for Bash, Zsh, Fish, etc.

mkdir -p "$LOCAL_BIN"

if [ -L "$LOCAL_BIN/brseqtb" ]; then
    rm "$LOCAL_BIN/brseqtb"
fi

ln -s "$WRAPPER_SRC" "$LOCAL_BIN/brseqtb"

echo "[OK] Created symlink: $LOCAL_BIN/brseqtb -> $WRAPPER_SRC"

# --------------------------------------------------
# Verify PATH
# --------------------------------------------------
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo ""
    echo "[NOTICE] $LOCAL_BIN is not in your PATH."
    echo "To fix this for all shells, add this line to your .bashrc or .zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    
    # Optional: Auto-add to bashrc if user is on bash
    if [ -f "$HOME/.bashrc" ] && [[ "$SHELL" == *"bash"* ]]; then
        if ! grep -Fq ".local/bin" "$HOME/.bashrc"; then
             echo "Adding to ~/.bashrc..."
             echo -e "\n# User local bin\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$HOME/.bashrc"
        fi
    fi
     # Optional: Auto-add to zshrc if user is on zsh
    if [ -f "$HOME/.zshrc" ] && [[ "$SHELL" == *"zsh"* ]]; then
        if ! grep -Fq ".local/bin" "$HOME/.zshrc"; then
             echo "Adding to ~/.zshrc..."
             echo -e "\n# User local bin\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$HOME/.zshrc"
        fi
    fi
fi

echo ""
echo "========================================="
echo " Installation complete!"
echo "========================================="
echo "You can now run 'brseqtb' from any directory."
echo "Note: Ensure your current directory has the 'input/' and 'reads/' folders."
