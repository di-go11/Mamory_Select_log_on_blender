bl_info = {
    "name": "Operation History Manager",
    "author": "Assistant",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > History",
    "description": "Record and restore multiple operation states",
    "category": "System",
}

import bpy
import bmesh
from bpy.props import *
from bpy.types import PropertyGroup, Panel, Operator, UIList
import json
import time


class HistoryEntry(PropertyGroup):
    name: StringProperty(
        name="Name", description="Name of this history entry", default="History Point"
    )

    timestamp: StringProperty(
        name="Timestamp", description="When this entry was created", default=""
    )

    data: StringProperty(name="Data", description="Serialized object data", default="")


class HISTORY_OT_save_state(Operator):
    bl_idname = "history.save_state"
    bl_label = "Save Current State"
    bl_description = "Save current state of selected objects"

    def execute(self, context):
        scene = context.scene
        history_props = scene.history_manager

        # アクティブオブジェクトの状態を保存
        if context.active_object and context.active_object.type == "MESH":
            obj = context.active_object

            # メッシュデータを辞書形式で保存
            mesh_data = self.serialize_mesh(obj)

            # 新しい履歴エントリを作成
            entry = history_props.history_list.add()
            entry.name = f"State {len(history_props.history_list)}"
            entry.timestamp = time.strftime("%H:%M:%S")
            entry.data = json.dumps(mesh_data)

            # 最大記録数を超えた場合は古いものを削除
            max_entries = history_props.max_history_count
            if len(history_props.history_list) > max_entries:
                history_props.history_list.remove(0)

            self.report({"INFO"}, f"State saved: {entry.name}")
        else:
            self.report({"WARNING"}, "No mesh object selected")
        print(f"name: {obj.name}")

        return {"FINISHED"}

    def serialize_mesh(self, obj):
        """メッシュオブジェクトをシリアライズ"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        # 正しいbmeshの作成方法
        bm = bmesh.from_edit_mesh(obj.data)  # Edit modeの場合

        # 頂点データ
        verts = [(v.co.x, v.co.y, v.co.z) for v in bm.verts]

        # 面データ
        faces = []
        for f in bm.faces:
            faces.append([v.index for v in f.verts])

        # エッジデータ
        edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges]

        bm.free()
        bpy.ops.object.mode_set(mode="OBJECT")

        return {
            "name": obj.name,
            "vertices": verts,
            "faces": faces,
            "edges": edges,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
        }


class HISTORY_OT_restore_state(Operator):
    bl_idname = "history.restore_state"
    bl_label = "Restore State"
    bl_description = "Restore selected history state"

    def execute(self, context):
        scene = context.scene
        history_props = scene.history_manager

        if (
            history_props.active_history_index < 0
            or history_props.active_history_index >= len(history_props.history_list)
        ):
            self.report({"WARNING"}, "No valid history entry selected")
            return {"CANCELLED"}

        if not context.active_object or context.active_object.type != "MESH":
            self.report({"WARNING"}, "No mesh object selected")
            return {"CANCELLED"}

        entry = history_props.history_list[history_props.active_history_index]

        try:
            mesh_data = json.loads(entry.data)
            self.restore_mesh(context.active_object, mesh_data)
            self.restore_mesh(mesh_data)
            self.report({"INFO"}, f"Restored state: {entry.name}")
        except Exception as e:
            self.report({"ERROR"}, f"Failed to restore state: {str(e)}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def restore_mesh(self, obj, mesh_data):
        """メッシュオブジェクトを復元"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        # Edit modeでbmeshを取得
        bm = bmesh.from_edit_mesh(obj.data)
        bm.clear()

        # 頂点を復元
        for vert_co in mesh_data["vertices"]:
            bm.verts.new(vert_co)

        bm.verts.ensure_lookup_table()

        # 面を復元
        for face_indices in mesh_data["faces"]:
            try:
                bm.faces.new([bm.verts[i] for i in face_indices])
            except:
                pass  # 無効な面はスキップ

        # メッシュを更新
        bmesh.update_edit_mesh(obj.data)

        bpy.ops.object.mode_set(mode="OBJECT")

        # トランスフォームを復元
        obj.location = mesh_data["location"]
        obj.rotation_euler = mesh_data["rotation"]
        obj.scale = mesh_data["scale"]


class HISTORY_OT_delete_entry(Operator):
    bl_idname = "history.delete_entry"
    bl_label = "Delete Entry"
    bl_description = "Delete selected history entry"

    def execute(self, context):
        scene = context.scene
        history_props = scene.history_manager

        if (
            history_props.active_history_index >= 0
            and history_props.active_history_index < len(history_props.history_list)
        ):
            history_props.history_list.remove(history_props.active_history_index)
            if history_props.active_history_index >= len(history_props.history_list):
                history_props.active_history_index = len(history_props.history_list) - 1
            self.report({"INFO"}, "History entry deleted")

        return {"FINISHED"}


class HISTORY_OT_clear_all(Operator):
    bl_idname = "history.clear_all"
    bl_label = "Clear All"
    bl_description = "Clear all history entries"

    def execute(self, context):
        scene = context.scene
        history_props = scene.history_manager
        history_props.history_list.clear()
        history_props.active_history_index = -1
        self.report({"INFO"}, "All history entries cleared")

        return {"FINISHED"}


class HISTORY_OT_auto_record_toggle(Operator):
    bl_idname = "history.auto_record_toggle"
    bl_label = "Toggle Auto Record"
    bl_description = "Toggle automatic recording of operations"

    def execute(self, context):
        scene = context.scene
        history_props = scene.history_manager
        history_props.auto_record = not history_props.auto_record

        status = "enabled" if history_props.auto_record else "disabled"
        self.report({"INFO"}, f"Auto record {status}")

        return {"FINISHED"}


class HISTORY_UL_list(UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=f"{item.name} ({item.timestamp})", icon="RECOVER_LAST")
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon="RECOVER_LAST")


class HistoryManagerProperties(PropertyGroup):
    history_list: CollectionProperty(type=HistoryEntry)
    active_history_index: IntProperty(name="Active History Index", default=-1)
    max_history_count: IntProperty(
        name="Max History Count",
        description="Maximum number of history entries to keep",
        default=10,
        min=1,
        max=50,
    )
    auto_record: bpy.props.BoolProperty(
        name="Auto Record",
        description="Automatically record states during operations",
        default=False,
    )


class VIEW3D_PT_history_manager(Panel):
    bl_label = "Operation History"
    bl_idname = "VIEW3D_PT_history_manager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "History"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        history_props = scene.history_manager

        # 設定セクション
        box = layout.box()
        box.label(text="Settings:", icon="PREFERENCES")
        box.prop(history_props, "max_history_count")

        # 自動記録ボタン
        row = box.row()
        if history_props.auto_record:
            row.operator(
                "history.auto_record_toggle", text="Stop Auto Record", icon="PAUSE"
            )
        else:
            row.operator(
                "history.auto_record_toggle", text="Start Auto Record", icon="REC"
            )

        layout.separator()

        # 操作ボタン
        row = layout.row(align=True)
        row.operator("history.save_state", text="Save State", icon="FILE_TICK")

        layout.separator()

        # 履歴リスト
        layout.label(text="History List:", icon="TIME")
        layout.template_list(
            "HISTORY_UL_list",
            "",
            history_props,
            "history_list",
            history_props,
            "active_history_index",
            rows=5,
        )

        # 履歴操作ボタン
        row = layout.row(align=True)
        row.operator("history.restore_state", text="Restore", icon="RECOVER_LAST")
        row.operator("history.delete_entry", text="Delete", icon="X")

        layout.operator("history.clear_all", text="Clear All", icon="TRASH")

        # 情報表示
        if len(history_props.history_list) > 0:
            layout.separator()
            layout.label(text=f"Total entries: {len(history_props.history_list)}")


# 自動記録用のハンドラー
def auto_record_handler(scene):
    history_props = scene.history_manager
    if (
        history_props.auto_record
        and bpy.context.active_object
        and bpy.context.active_object.type == "MESH"
    ):
        # 一定間隔で自動保存（この例では簡略化）
        pass


classes = [
    HistoryEntry,
    HistoryManagerProperties,
    HISTORY_OT_save_state,
    HISTORY_OT_restore_state,
    HISTORY_OT_delete_entry,
    HISTORY_OT_clear_all,
    HISTORY_OT_auto_record_toggle,
    HISTORY_UL_list,
    VIEW3D_PT_history_manager,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.history_manager = bpy.props.PointerProperty(
        type=HistoryManagerProperties
    )

    # ハンドラーを登録（オプション）
    # bpy.app.handlers.depsgraph_update_post.append(auto_record_handler)


def unregister():
    # ハンドラーを削除
    # if auto_record_handler in bpy.app.handlers.depsgraph_update_post:
    #     bpy.app.handlers.depsgraph_update_post.remove(auto_record_handler)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.history_manager


if __name__ == "__main__":
    register()
