#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "→ Checking Python..."
python3 --version

echo "→ Creating virtual environment..."
python3 -m venv .venv

echo "→ Activating virtual environment..."
source .venv/bin/activate

echo "→ Installing Python dependencies..."
pip install -r requirements.txt

echo "→ Verifying FFmpeg..."
.venv/bin/python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"

echo "✓ Setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run content-os:"
echo "  python cli.py"
