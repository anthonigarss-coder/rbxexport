"""Tests inside real Blender (the `bpy` module). Skipped when bpy is not installed.

Run with a Python that has bpy:   python -m pytest tests/test_blender.py
"""

import sys
from pathlib import Path

import pytest

bpy = pytest.importorskip("bpy")
import addon_utils  # noqa: E402
import bmesh  # noqa: E402

sys.path.insert(0, str(Path(__file__).parents[1]))
import roblox_export  # noqa: E402


@pytest.fixture(autouse=True)
def scene(tmp_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_scene_fbx", default_set=False)
    roblox_export.register()
    s = bpy.context.scene.rbx_export
    s.folder = str(tmp_path / "out")
    yield bpy.context.scene
    roblox_export.unregister()


def make_cube(name, location=(0, 0, 0), size=1.0):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def select_only(*objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def run(op):
    """Call an operator. Blender raises RuntimeError when an operator reports an ERROR."""
    try:
        return op()
    except RuntimeError as e:
        return {"CANCELLED", str(e)}


def issue_codes():
    return [(i.object_name, i.code) for i in bpy.context.scene.rbx_export.issues]


def test_registers_and_unregisters_cleanly():
    assert hasattr(bpy.context.scene, "rbx_export")
    assert hasattr(bpy.ops.rbx, "check") and hasattr(bpy.ops.rbx, "export")


def test_clean_cube_has_no_issues():
    select_only(make_cube("Crate"))
    assert bpy.ops.rbx.check() == {"FINISHED"}
    assert issue_codes() == []


def test_nothing_selected_is_reported_not_crashing():
    make_cube("Crate")
    select_only()  # deselect all
    assert "CANCELLED" in run(bpy.ops.rbx.check)
    assert "CANCELLED" in run(bpy.ops.rbx.export)


def test_unapplied_scale_and_negative_scale():
    a = make_cube("Big")
    a.scale = (2, 2, 2)
    b = make_cube("Flipped", (3, 0, 0))
    b.scale = (-1, 1, 1)
    select_only(a, b)
    bpy.ops.rbx.check()
    assert ("Big", "SCALE_NOT_APPLIED") in issue_codes()
    assert ("Flipped", "NEGATIVE_SCALE") in issue_codes()


def test_triangle_count_includes_modifiers():
    obj = make_cube("Smooth")
    mod = obj.modifiers.new("sub", "SUBSURF")
    mod.levels = 6  # 12 tris -> 49,152 after the modifier
    select_only(obj)
    bpy.ops.rbx.check()
    assert ("Smooth", "TOO_MANY_TRIS") in issue_codes()
    # ...and the same object is fine with a higher limit
    bpy.context.scene.rbx_export.max_tris = 1_000_000
    bpy.ops.rbx.check()
    assert ("Smooth", "TOO_MANY_TRIS") not in issue_codes()


def test_no_uv_and_materials():
    mesh = bpy.data.meshes.new("NoUV")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new("NoUV", mesh)
    bpy.context.collection.objects.link(obj)

    multi = make_cube("Multi", (3, 0, 0))
    for n in ("m1", "m2"):
        multi.data.materials.append(bpy.data.materials.new(n))
    multi.data.polygons[0].material_index = 1

    empty = make_cube("EmptySlot", (6, 0, 0))
    empty.data.materials.append(bpy.data.materials.new("only"))
    empty.data.materials.append(None)
    empty.data.polygons[0].material_index = 1

    select_only(obj, multi, empty)
    bpy.ops.rbx.check()
    found = issue_codes()
    assert ("NoUV", "NO_UV") in found
    assert ("Multi", "MULTI_MATERIAL") in found
    assert ("EmptySlot", "EMPTY_MATERIAL_SLOT") in found


def test_export_one_file_per_object_and_restores_selection(tmp_path):
    a, b, c = make_cube("Crate"), make_cube("Door/Frame", (3, 0, 0)), make_cube("Other", (6, 0, 0))
    select_only(a, b)
    assert bpy.ops.rbx.export() == {"FINISHED"}
    out = tmp_path / "out"
    assert sorted(p.name for p in out.glob("*.fbx")) == ["Crate.fbx", "Door_Frame.fbx"]
    for f in out.glob("*.fbx"):
        assert f.read_bytes().startswith(b"Kaydara FBX Binary")
    assert {o.name for o in bpy.context.selected_objects} == {"Crate", "Door/Frame"}
    assert bpy.context.view_layer.objects.active == a
    assert not c.select_get()


def test_export_single_file_with_clean_name(tmp_path):
    a, b = make_cube("A"), make_cube("B", (3, 0, 0))
    select_only(a, b)
    s = bpy.context.scene.rbx_export
    s.separate_files = False
    s.file_name = "my:model"
    assert bpy.ops.rbx.export() == {"FINISHED"}
    assert [p.name for p in (tmp_path / "out").glob("*.fbx")] == ["my_model.fbx"]


def test_errors_block_export_unless_allowed(tmp_path):
    obj = make_cube("Heavy")
    obj.modifiers.new("sub", "SUBSURF").levels = 6
    select_only(obj)
    assert "CANCELLED" in run(bpy.ops.rbx.export)
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.fbx"))
    bpy.context.scene.rbx_export.allow_errors = True
    assert bpy.ops.rbx.export() == {"FINISHED"}
    assert (tmp_path / "out" / "Heavy.fbx").exists()


def test_visible_scope_skips_hidden_and_non_meshes(tmp_path):
    shown, hidden = make_cube("Shown"), make_cube("Hidden", (3, 0, 0))
    hidden.hide_set(True)
    bpy.ops.object.empty_add(location=(9, 0, 0))
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.scene.rbx_export.scope = "VISIBLE"
    assert bpy.ops.rbx.export() == {"FINISHED"}
    assert [p.name for p in (tmp_path / "out").glob("*.fbx")] == ["Shown.fbx"]


def test_duplicate_safe_names_do_not_overwrite(tmp_path):
    a, b = make_cube("a/b"), make_cube("a:b", (3, 0, 0))
    select_only(a, b)
    assert bpy.ops.rbx.export() == {"FINISHED"}
    assert sorted(p.name for p in (tmp_path / "out").glob("*.fbx")) == ["a_b.fbx", "a_b_2.fbx"]


def test_exported_fbx_can_be_read_by_rbxcheck(tmp_path):
    try:
        from rbxcheck.parsers import fbx  # type: ignore  # pip install rbxcheck
    except ImportError:
        pytest.skip("rbxcheck not installed")

    select_only(make_cube("Crate"))
    bpy.ops.rbx.export()
    parsed = fbx.parse(tmp_path / "out" / "Crate.fbx")
    assert len(parsed.meshes) == 1
