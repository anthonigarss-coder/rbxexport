# rbxexport

A Blender add-on that **checks your meshes and exports them to Roblox Studio** with the right FBX settings, in two clicks.

No more "why is my model 100 times too big", "Roblox rejected my mesh", or forgetting to apply the scale.

- **Check** finds problems before Studio does: more than 20,000 triangles (counted *after* modifiers), unapplied or negative scale, missing UV map, several materials, empty material slots.
- **Export** writes FBX files with the settings Roblox recommends: *FBX Unit Scale*, no leaf bones, textures copied and embedded, animation baking off unless you ask for it.
- One FBX **per object** (named after the object) or a single file for the whole selection.
- Stops if there are errors (you can override it), and puts your selection back as it was.

Blender 4.2 or newer. MIT license.

## Install

1. Download [`downloads/roblox_export-0.1.0.zip`](downloads/roblox_export-0.1.0.zip) (do not unzip it).
2. In Blender: **Edit > Preferences > Get Extensions**, open the small arrow menu at the top right, **Install from Disk...**, pick the zip.
   (You can also drag the zip into the Blender window.)
3. In the 3D viewport press **N**: a **Roblox** tab appears in the sidebar.

## Use

1. Select your meshes (or choose *Visible* to take every visible mesh).
2. Pick the output folder. `//roblox_export/` means a folder next to your `.blend` file.
3. Press **Check** to read the problems, then **Export**.
4. In Studio: **Home > Import 3D** and pick the FBX files.

You can also use **File > Export > Roblox (.fbx)**, it does the same thing with the panel settings.

### Settings

| setting | meaning |
|---|---|
| Folder | where the FBX files go |
| Objects | `Selected` or `Visible` mesh objects |
| One file per object | one FBX per object, named after it (names are cleaned, and made unique if two collide) |
| Triangle limit | meshes above it are errors (Roblox: 20,000) |
| Include animation | bake animation into the FBX (leave off for static models) |
| Export even with errors | write the files even if Check found errors |

### What Check reports

| level | code | meaning |
|---|---|---|
| error | `TOO_MANY_TRIS` | over the triangle limit after modifiers |
| error | `NO_GEOMETRY` | the object has no faces |
| warning | `SCALE_NOT_APPLIED` | object scale is not 1, size in Studio may surprise you |
| warning | `NEGATIVE_SCALE` | faces may look inside-out |
| warning | `NO_UV` | a texture cannot be shown |
| warning | `EMPTY_MATERIAL_SLOT` | faces use a slot with no material |
| note | `MULTI_MATERIAL` | Studio will split the mesh into one MeshPart per material |

Pairs well with [rbxcheck](https://github.com/anthonigarss-coder/rbxcheck), which validates the exported file itself from the command line.

## Develop

```bash
python build.py                      # builds dist/roblox_export-<version>.zip
python -m pytest tests/test_core.py  # logic tests, plain Python
pip install bpy pytest && python -m pytest   # all tests, inside Blender's Python module
```

`roblox_export/core.py` has no Blender import, so the rules are tested without Blender. `ops.py` and `ui.py` are the thin Blender layer.

## License

MIT
