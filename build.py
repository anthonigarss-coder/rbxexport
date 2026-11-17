"""Build dist/roblox_export-<version>.zip, ready for Blender > Extensions > Install from Disk."""

import re
import zipfile
from pathlib import Path

root = Path(__file__).parent
src = root / "roblox_export"
version = re.search(r'^version = "(.+)"', (src / "blender_manifest.toml").read_text(), re.M).group(1)
out = root / "dist" / f"roblox_export-{version}.zip"
out.parent.mkdir(exist_ok=True)

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
            z.write(f, f.relative_to(src).as_posix())  # manifest must sit at the zip root
print(out)
