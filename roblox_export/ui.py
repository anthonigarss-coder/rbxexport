"""Sidebar panel (View3D > N panel > Roblox) and File > Export entry."""

import bpy
from bpy.types import Panel

from . import core, ops

_ICON = {core.ERROR: "ERROR", core.WARNING: "INFO", core.INFO: "DOT"}
_MAX_LINES = 12


class RBX_PT_main(Panel):
    bl_label = "Roblox Export"
    bl_idname = "RBX_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Roblox"

    def draw(self, context):
        s = context.scene.rbx_export
        col = self.layout.column(align=True)
        col.prop(s, "folder")
        col.prop(s, "scope", expand=True)
        col.prop(s, "separate_files")
        if not s.separate_files:
            col.prop(s, "file_name")
        col.prop(s, "max_tris")
        col.prop(s, "include_animation")
        col.prop(s, "allow_errors")

        row = self.layout.row(align=True)
        row.operator(ops.RBX_OT_check.bl_idname, icon="CHECKMARK")
        row.operator(ops.RBX_OT_export.bl_idname, icon="EXPORT")

        if s.issues:
            box = self.layout.box()
            counts = {core.ERROR: 0, core.WARNING: 0, core.INFO: 0}
            for i in s.issues:
                counts[i.severity] += 1
            box.label(
                text=f"{counts[core.ERROR]} error(s), {counts[core.WARNING]} warning(s), "
                f"{counts[core.INFO]} note(s)"
            )
            for i in list(s.issues)[:_MAX_LINES]:
                box.label(text=f"{i.object_name}: {i.text}", icon=_ICON[i.severity])
            if len(s.issues) > _MAX_LINES:
                box.label(text=f"... and {len(s.issues) - _MAX_LINES} more")


def _menu_export(self, context):
    self.layout.operator(ops.RBX_OT_export.bl_idname, text="Roblox (.fbx)")


def register():
    bpy.utils.register_class(RBX_PT_main)
    bpy.types.TOPBAR_MT_file_export.append(_menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu_export)
    bpy.utils.unregister_class(RBX_PT_main)
