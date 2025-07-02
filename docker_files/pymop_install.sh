#!/bin/bash
set -e  # Exit on error

echo "Creating a virtual environment for PyMOP..."
python3 -m venv /workspace/pymop-venv
source /workspace/pymop-venv/bin/activate

echo "Installing dependencies..."
pip install pytest-json-report
pip install /workspace/pymop-artifacts-rv/pymop/

echo "Installation complete."
deactivate