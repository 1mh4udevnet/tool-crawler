import PyInstaller.__main__
import os
import shutil

# Project name
APP_NAME = "ToolCraw"

# Define the build command
# --onefile: single exe
# --noconsole: don't show terminal
# --name: output name
# --hidden-import: ensure submodules are included if needed
# --add-data: include app folder structure (app/*.py)
# We don't strictly need --add-data for the .py files if they are imported, 
# but PyInstaller usually handles imports automatically.
# However, if there were static assets, we'd add them here.

PyInstaller.__main__.run([
    'ui.py',
    '--onefile',
    '--windowed',
    '--name=%s' % APP_NAME,
    '--icon=assets/app_icon.ico',
    '--clean',
])

print(f"\nDone! Your app is in the 'dist' folder as {APP_NAME}.exe")
