"""Tests of the pure logic. They run with plain Python, no Blender needed."""

import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "rbx_core", Path(__file__).parents[1] / "roblox_export" / "core.py"
)
core = importlib.util.module_from_spec(_spec)
sys.modules["rbx_core"] = core  # dataclasses needs the module to be registered
_spec.loader.exec_module(core)  # type: ignore[union-attr]

I = core.ObjectInfo


def codes(issues):
    return [i.code for i in issues]


def test_clean_object_has_no_issue():
    assert core.check_object(I("Crate", tris=12)) == []


def test_empty_object_is_an_error_and_stops_there():
    out = core.check_object(I("Ghost", tris=0, has_uv=False))
    assert codes(out) == ["NO_GEOMETRY"] and out[0].severity == core.ERROR


@pytest.mark.parametrize("tris,bad", [(20_000, False), (20_001, True)])
def test_triangle_limit_edge(tris, bad):
    assert ("TOO_MANY_TRIS" in codes(core.check_object(I("A", tris=tris)))) is bad


def test_triangle_limit_is_configurable_and_message_counts_excess():
    (issue,) = core.check_object(I("A", tris=1500), max_tris=1000)
    assert issue.code == "TOO_MANY_TRIS" and "500" in issue.message


@pytest.mark.parametrize(
    "scale,expected",
    [
        ((1, 1, 1), []),
        ((1.00001, 1, 1), []),  # rounding noise is ignored
        ((2, 2, 2), ["SCALE_NOT_APPLIED"]),
        ((1, 1, 0.5), ["SCALE_NOT_APPLIED"]),
        ((-1, 1, 1), ["NEGATIVE_SCALE"]),  # -1 is "applied" but flipped
        ((-2, 1, 1), ["SCALE_NOT_APPLIED", "NEGATIVE_SCALE"]),
    ],
)
def test_scale_checks(scale, expected):
    assert codes(core.check_object(I("A", tris=12, scale=scale))) == expected


def test_uv_and_material_checks():
    out = core.check_object(I("A", tris=12, has_uv=False, materials_used=3, empty_slot_used=True))
    assert set(codes(out)) == {"NO_UV", "MULTI_MATERIAL", "EMPTY_MATERIAL_SLOT"}
    multi = next(i for i in out if i.code == "MULTI_MATERIAL")
    assert multi.severity == core.INFO and "3 MeshParts" in multi.message


def test_check_all_sorts_errors_first_and_counts():
    issues = core.check_all(
        [I("B", tris=12, has_uv=False), I("A", tris=99_999), I("C", tris=12, materials_used=2)]
    )
    assert [i.severity for i in issues] == [core.ERROR, core.WARNING, core.INFO]
    assert core.count(issues) == {core.ERROR: 1, core.WARNING: 1, core.INFO: 1}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Cube", "Cube"),
        ("My Crate.001", "My Crate.001"),
        ('a/b\\c:d*e?f"g<h>i|j', "a_b_c_d_e_f_g_h_i_j"),
        ("  ..name.. ", "name"),
        ("", "export"),
        ("...", "export"),
    ],
)
def test_safe_filename(raw, expected):
    assert core.safe_filename(raw) == expected


def test_unique_names_handles_collisions_case_insensitively():
    assert core.unique_names(["A/B", "A:B", "a_b", "C"]) == ["A_B", "A_B_2", "a_b_3", "C"]


def test_fbx_kwargs_follow_roblox_guide():
    kw = core.fbx_kwargs(core.ExportOptions(), "x.fbx")
    assert kw["apply_scale_options"] == "FBX_SCALE_UNITS"
    assert kw["add_leaf_bones"] is False and kw["bake_anim"] is False
    assert kw["path_mode"] == "COPY" and kw["embed_textures"] is True
    assert kw["use_selection"] is True and kw["use_mesh_modifiers"] is True
    assert core.fbx_kwargs(core.ExportOptions(include_animation=True), "x.fbx")["bake_anim"] is True
    assert core.fbx_kwargs(core.ExportOptions(extra={"global_scale": 0.5}), "x.fbx")["global_scale"] == 0.5
