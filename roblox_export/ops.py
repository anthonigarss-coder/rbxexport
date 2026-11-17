"""Blender operators: check the meshes, then export them as Roblox-ready FBX."""

from __future__ import annotations

import os

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, PropertyGroup

from . import core


# ----------------------------------------------------------------- settings
class RBX_Issue(PropertyGroup):
    severity: StringProperty()
    code: StringProperty()
    object_name: StringProperty()
    text: StringProperty()


class RBX_Settings(PropertyGroup):
    folder: StringProperty(
        name="Folder",
        description="Where the FBX files are written ('//' means next to the .blend file)",
        subtype="DIR_PATH",
        default="//roblox_export/",
    )
    scope: EnumProperty(
        name="Objects",
        items=[
            ("SELECTED", "Selected", "Only the selected mesh objects"),
            ("VISIBLE", "Visible", "Every visible mesh object in the scene"),
        ],
        default="SELECTED",
    )
    separate_files: BoolProperty(
        name="One file per object",
        description="Write one FBX per object (named after the object) instead of a single file",
        default=True,
    )
    file_name: StringProperty(
        name="File name",
        description="Name of the FBX when 'One file per object' is off",
        default="model",
    )
    max_tris: IntProperty(
        name="Triangle limit",
        description="Meshes above this are reported as errors (Roblox limit: 20,000)",
        default=core.MAX_TRIS_DEFAULT,
        min=1,
    )
    include_animation: BoolProperty(
        name="Include animation",
        description="Bake animation into the FBX. Leave off for static models",
        default=False,
    )
    allow_errors: BoolProperty(
        name="Export even with errors",
        description="Write the files even when the check found errors",
        default=False,
    )
    issues: CollectionProperty(type=RBX_Issue)


# ------------------------------------------------------------------ helpers
def target_objects(context, scope: str):
    if scope == "SELECTED":
        pool = context.selected_objects
    else:
        pool = [o for o in context.scene.objects if o.visible_get()]
    return [o for o in pool if o.type == "MESH"]


def object_info(obj, depsgraph) -> core.ObjectInfo:
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        has_uv = len(me.uv_layers) > 0
        used_slots = {p.material_index for p in me.polygons}
        slots = list(obj.material_slots)
        mats = set()
        empty_used = False
        for idx in used_slots:
            mat = slots[idx].material if idx < len(slots) else None
            if mat is None:
                empty_used = True
            else:
                mats.add(mat.name)
        # a mesh with no slots at all is simply unmaterialed, not an error
        if not slots:
            empty_used = False
    finally:
        ev.to_mesh_clear()
    return core.ObjectInfo(
        name=obj.name,
        tris=tris,
        scale=tuple(obj.scale),
        has_uv=has_uv,
        materials_used=len(mats),
        empty_slot_used=empty_used,
    )


def run_checks(context, objs, max_tris):
    dg = context.evaluated_depsgraph_get()
    infos = [object_info(o, dg) for o in objs]
    return core.check_all(infos, max_tris)


def store_issues(settings, issues):
    settings.issues.clear()
    for i in issues:
        it = settings.issues.add()
        it.severity, it.code, it.object_name, it.text = (
            i.severity,
            i.code,
            i.object,
            i.message,
        )


def _supported(op, kwargs: dict) -> dict:
    """Keep only the arguments this Blender version's FBX exporter knows."""
    known = {p.identifier for p in op.get_rna_type().properties}
    return {k: v for k, v in kwargs.items() if k in known}


# ---------------------------------------------------------------- operators
class RBX_OT_check(Operator):
    bl_idname = "rbx.check"
    bl_label = "Check"
    bl_description = "Look for problems that Roblox Studio would reject or show wrong"

    def execute(self, context):
        s = context.scene.rbx_export
        objs = target_objects(context, s.scope)
        if not objs:
            store_issues(s, [])
            self.report({"WARNING"}, "No mesh objects to check")
            return {"CANCELLED"}
        issues = run_checks(context, objs, s.max_tris)
        store_issues(s, issues)
        c = core.count(issues)
        level = {"WARNING"} if c[core.ERROR] else {"INFO"}
        self.report(
            level,
            f"{len(objs)} object(s): {c[core.ERROR]} error(s), "
            f"{c[core.WARNING]} warning(s), {c[core.INFO]} note(s)",
        )
        return {"FINISHED"}


class RBX_OT_export(Operator):
    bl_idname = "rbx.export"
    bl_label = "Export for Roblox"
    bl_description = "Check the meshes, then write FBX files with Roblox's recommended settings"

    def execute(self, context):
        s = context.scene.rbx_export
        if not hasattr(bpy.ops.export_scene, "fbx"):
            self.report({"ERROR"}, "The FBX exporter add-on is disabled in Preferences")
            return {"CANCELLED"}

        objs = target_objects(context, s.scope)
        if not objs:
            self.report({"ERROR"}, "No mesh objects to export")
            return {"CANCELLED"}

        issues = run_checks(context, objs, s.max_tris)
        store_issues(s, issues)
        c = core.count(issues)
        if c[core.ERROR] and not s.allow_errors:
            self.report(
                {"ERROR"},
                f"{c[core.ERROR]} error(s) found, nothing exported. "
                "Fix them or turn on 'Export even with errors'",
            )
            return {"CANCELLED"}

        folder = bpy.path.abspath(s.folder)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            self.report({"ERROR"}, f"Cannot create folder: {e}")
            return {"CANCELLED"}

        opts = core.ExportOptions(include_animation=s.include_animation)
        if s.separate_files:
            stems = core.unique_names([o.name for o in objs])
            jobs = [([o], stem) for o, stem in zip(objs, stems)]
        else:
            jobs = [(objs, core.safe_filename(s.file_name))]

        view_layer = context.view_layer
        old_selected = list(context.selected_objects)
        old_active = view_layer.objects.active
        written = []
        try:
            for group, stem in jobs:
                for o in context.view_layer.objects:
                    o.select_set(False)
                for o in group:
                    o.select_set(True)
                view_layer.objects.active = group[0]
                path = os.path.join(folder, stem + ".fbx")
                kw = _supported(bpy.ops.export_scene.fbx, core.fbx_kwargs(opts, path))
                result = bpy.ops.export_scene.fbx(**kw)
                if "FINISHED" not in result:
                    self.report({"ERROR"}, f"Export of {stem} failed")
                    return {"CANCELLED"}
                written.append(path)
        finally:
            for o in context.view_layer.objects:
                o.select_set(False)
            for o in old_selected:
                if o.name in context.view_layer.objects:
                    o.select_set(True)
            view_layer.objects.active = old_active

        self.report({"INFO"}, f"Exported {len(written)} file(s) to {folder}")
        return {"FINISHED"}


CLASSES = (RBX_Issue, RBX_Settings, RBX_OT_check, RBX_OT_export)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.rbx_export = PointerProperty(type=RBX_Settings)


def unregister():
    del bpy.types.Scene.rbx_export
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
