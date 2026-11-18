"""
download_stockfish.py — Download official Stockfish Windows binary into backend/stockfish/
"""

import sys
import os
import zipfile
import urllib.request
from pathlib import Path

STOCKFISH_ZIP_URL = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
TARGET_DIR = Path(__file__).parent.parent / "backend" / "stockfish"
TARGET_EXE = TARGET_DIR / "stockfish.exe"

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET_EXE.exists():
        print(f"Stockfish binary already present at: {TARGET_EXE}")
        return

    print(f"Downloading Stockfish from {STOCKFISH_ZIP_URL}...")
    temp_zip = TARGET_DIR / "stockfish_temp.zip"
    try:
        urllib.request.urlretrieve(STOCKFISH_ZIP_URL, temp_zip)
        print("Extracting...")
        with zipfile.ZipFile(temp_zip, "r") as z:
            for member in z.namelist():
                if member.endswith(".exe"):
                    source = z.open(member)
                    with open(TARGET_EXE, "wb") as target:
                        target.write(source.read())
                    print(f"Extracted {member} -> {TARGET_EXE}")
                    break
        temp_zip.unlink(missing_ok=True)
        print("Stockfish setup completed successfully!")
    except Exception as e:
        print(f"Failed to download automatically: {e}")
        print("Manual setup: Download Stockfish for Windows from https://stockfishchess.org/download/")
        print(f"and place the extracted stockfish.exe into: {TARGET_DIR}")

if __name__ == "__main__":
    main()
