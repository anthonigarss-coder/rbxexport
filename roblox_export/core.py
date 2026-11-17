"""Pure-Python logic (no Blender import), so it can be tested without Blender.

The Blender layer (ops.py) reads the scene, builds ObjectInfo values, and uses
the functions here to decide what is a problem and which export options to use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Roblox rejects meshes with more than 20,000 triangles.
MAX_TRIS_DEFAULT = 20_000

ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"

_SCALE_EPS = 1e-4


@dataclass(frozen=True)
class ObjectInfo:
    """What the checks need to know about one mesh object (after modifiers)."""

    name: str
    tris: int
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    has_uv: bool = True
    materials_used: int = 1  # distinct materials really used by faces
    empty_slot_used: bool = False  # faces that use a slot with no material


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    object: str
    message: str


def check_object(info: ObjectInfo, max_tris: int = MAX_TRIS_DEFAULT) -> list[Issue]:
    out: list[Issue] = []
    n = info.name

    if info.tris == 0:
        out.append(Issue(ERROR, "NO_GEOMETRY", n, "has no faces, nothing to export"))
        return out

    if info.tris > max_tris:
        out.append(
            Issue(
                ERROR,
                "TOO_MANY_TRIS",
                n,
                f"{info.tris:,} triangles, Roblox accepts at most {max_tris:,} per mesh "
                f"(too many by {info.tris - max_tris:,})",
            )
        )

    if any(abs(abs(s) - 1.0) > _SCALE_EPS for s in info.scale):
        sx, sy, sz = info.scale
        out.append(
            Issue(
                WARNING,
                "SCALE_NOT_APPLIED",
                n,
                f"object scale is ({sx:.3g}, {sy:.3g}, {sz:.3g}), not 1. "
                "Apply it (Ctrl+A > Scale) so the size in Studio is predictable",
            )
        )

    if any(s < 0 for s in info.scale):
        out.append(
            Issue(
                WARNING,
                "NEGATIVE_SCALE",
                n,
                "negative scale flips the faces, the mesh may look inside-out in Studio",
            )
        )

    if not info.has_uv:
        out.append(
            Issue(WARNING, "NO_UV", n, "no UV map, a texture cannot be shown on it")
        )

    if info.materials_used > 1:
        out.append(
            Issue(
                INFO,
                "MULTI_MATERIAL",
                n,
                f"uses {info.materials_used} materials, Studio will split it into "
                f"{info.materials_used} MeshParts",
            )
        )

    if info.empty_slot_used:
        out.append(
            Issue(
                WARNING,
                "EMPTY_MATERIAL_SLOT",
                n,
                "some faces use a material slot with no material",
            )
        )
    return out


def check_all(infos: list[ObjectInfo], max_tris: int = MAX_TRIS_DEFAULT) -> list[Issue]:
    issues: list[Issue] = []
    for info in infos:
        issues.extend(check_object(info, max_tris))
    order = {ERROR: 0, WARNING: 1, INFO: 2}
    issues.sort(key=lambda i: (order[i.severity], i.object, i.code))
    return issues


def count(issues: list[Issue]) -> dict[str, int]:
    c = {ERROR: 0, WARNING: 0, INFO: 0}
    for i in issues:
        c[i.severity] += 1
    return c


# --------------------------------------------------------------------- files
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(name: str) -> str:
    """A name that is valid as a file name on Windows, macOS and Linux."""
    cleaned = _BAD.sub("_", name).strip(" .")
    return cleaned or "export"


def unique_names(names: list[str]) -> list[str]:
    """Safe file stems for names, adding _2, _3... when two collapse to the same stem."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for n in names:
        stem = safe_filename(n)
        key = stem.lower()
        seen[key] = seen.get(key, 0) + 1
        out.append(stem if seen[key] == 1 else f"{stem}_{seen[key]}")
    return out


# ------------------------------------------------------------------- options
@dataclass
class ExportOptions:
    include_animation: bool = False
    extra: dict = field(default_factory=dict)


def fbx_kwargs(opts: ExportOptions, filepath: str) -> dict:
    """Arguments for bpy.ops.export_scene.fbx, following Roblox's export guide:
    FBX Unit Scale, no leaf bones, textures copied and embedded, animation baking
    off unless the model is animated."""
    kw = {
        "filepath": filepath,
        "use_selection": True,
        "object_types": {"MESH", "ARMATURE"},
        "use_mesh_modifiers": True,
        "apply_scale_options": "FBX_SCALE_UNITS",
        "axis_forward": "-Z",
        "axis_up": "Y",
        "add_leaf_bones": False,
        "bake_anim": opts.include_animation,
        "path_mode": "COPY",
        "embed_textures": True,
    }
    kw.update(opts.extra)
    return kw
