import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_zip_has_manifest_at_root_and_no_junk(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "build.py")], check=True, capture_output=True)
    (z,) = (ROOT / "dist").glob("roblox_export-*.zip")
    names = zipfile.ZipFile(z).namelist()
    assert "blender_manifest.toml" in names and "__init__.py" in names
    assert not any("__pycache__" in n or n.endswith(".pyc") for n in names)


def test_manifest_fields():
    import tomllib

    m = tomllib.loads((ROOT / "roblox_export" / "blender_manifest.toml").read_text())
    assert m["id"] == "roblox_export" and m["type"] == "add-on"
    assert len(m["tagline"]) <= 64 and not m["tagline"].endswith(".")
    assert "files" in m["permissions"]
