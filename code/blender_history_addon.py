bl_info = {
    "name": "Operation History Manager",
    "author": "Assistant",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > History",
    "description": "Record and restore multiple operation states with UUID support",
    "category": "System",
}

import bpy
import bmesh
from bpy.props import *
from bpy.types import PropertyGroup, Panel, Operator, UIList
import json
import time
import uuid


class HistoryEntry(PropertyGroup):
    name: StringProperty(
        name="Name", description="Name of this history entry", default="History Point"
    )

    timestamp: StringProperty(
        name="Timestamp", description="When this entry was created", default=""
    )

    data: StringProperty(name="Data", description="Serialized object data", default="")

    object_uuid: StringProperty(
        name="Object UUID",
        description="UUID of the object this entry belongs to",
        default="",
    )

    object_name: StringProperty(
        name="Object Name", description="Name of the object when saved", default=""
    )


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

            # オブジェクトのUUIDを取得または生成
            obj_uuid = self.get_or_create_uuid(obj)

            # メッシュデータを辞書形式で保存
            mesh_data = self.serialize_mesh(obj)

            # 新しい履歴エントリを作成
            entry = history_props.history_list.add()
            entry.name = f"{obj.name}_State_{len([e for e in history_props.history_list if e.object_uuid == obj_uuid])}"
            entry.timestamp = time.strftime("%H:%M:%S")
            entry.data = json.dumps(mesh_data)
            entry.object_uuid = obj_uuid
            entry.object_name = obj.name

            # オブジェクトごとの最大記録数をチェック
            self.cleanup_old_entries(history_props, obj_uuid)

            self.report({"INFO"}, f"State saved: {entry.name}")
            print(f"Saved state for object: {obj.name} (UUID: {obj_uuid})")
        else:
            self.report({"WARNING"}, "No mesh object selected")

        return {"FINISHED"}

    def get_or_create_uuid(self, obj):
        """オブジェクトのUUIDを取得または新規作成"""
        if "history_uuid" not in obj:
            obj["history_uuid"] = str(uuid.uuid4())
        return obj["history_uuid"]

    def cleanup_old_entries(self, history_props, obj_uuid):
        """指定されたオブジェクトの古い履歴エントリを削除"""
        max_entries = history_props.max_history_count

        # 対象オブジェクトのエントリのみを取得
        obj_entries = [
            (i, entry)
            for i, entry in enumerate(history_props.history_list)
            if entry.object_uuid == obj_uuid
        ]

        # 最大数を超えた場合は古いものから削除
        if len(obj_entries) > max_entries:
            entries_to_remove = len(obj_entries) - max_entries
            for i in range(entries_to_remove):
                # 最も古いエントリのインデックスを取得して削除
                oldest_index = obj_entries[i][0]
                # インデックス調整（削除により前にずれる）
                adjusted_index = oldest_index - i
                history_props.history_list.remove(adjusted_index)

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

        entry = history_props.history_list[history_props.active_history_index]

        # UUIDに基づいて対象オブジェクトを検索
        target_obj = self.find_object_by_uuid(entry.object_uuid)

        if not target_obj:
            self.report({"WARNING"}, f"Object with UUID {entry.object_uuid} not found")
            return {"CANCELLED"}

        if target_obj.type != "MESH":
            self.report({"WARNING"}, "Target object is not a mesh")
            return {"CANCELLED"}

        try:
            mesh_data = json.loads(entry.data)
            self.restore_mesh(target_obj, mesh_data)
            self.report({"INFO"}, f"Restored state: {entry.name} to {target_obj.name}")
        except Exception as e:
            self.report({"ERROR"}, f"Failed to restore state: {str(e)}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def find_object_by_uuid(self, obj_uuid):
        """UUIDでオブジェクトを検索"""
        for obj in bpy.data.objects:
            if obj.get("history_uuid") == obj_uuid:
                return obj
        return None

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
            entry = history_props.history_list[history_props.active_history_index]
            history_props.history_list.remove(history_props.active_history_index)
            if history_props.active_history_index >= len(history_props.history_list):
                history_props.active_history_index = len(history_props.history_list) - 1
            self.report({"INFO"}, f"History entry {entry.name} deleted")

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


class HISTORY_OT_clear_object_history(Operator):
    bl_idname = "history.clear_object_history"
    bl_label = "Clear Object History"
    bl_description = "Clear history entries for the active object only"

    def execute(self, context):
        scene = context.scene
        history_props = scene.history_manager

        if not context.active_object:
            self.report({"WARNING"}, "No active object")
            return {"CANCELLED"}

        obj = context.active_object
        obj_uuid = obj.get("history_uuid")

        if not obj_uuid:
            self.report({"INFO"}, "No history found for this object")
            return {"FINISHED"}

        # 対象オブジェクトのエントリを削除
        entries_to_remove = []
        for i, entry in enumerate(history_props.history_list):
            if entry.object_uuid == obj_uuid:
                entries_to_remove.append(i)

        # 後ろから削除（インデックスがずれないように）
        for i in reversed(entries_to_remove):
            history_props.history_list.remove(i)

        # アクティブインデックスを調整
        if history_props.active_history_index >= len(history_props.history_list):
            history_props.active_history_index = len(history_props.history_list) - 1

        self.report(
            {"INFO"}, f"Cleared {len(entries_to_remove)} entries for {obj.name}"
        )

        return {"FINISHED"}


"""
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
"""


class HISTORY_UL_list(UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # オブジェクト名とタイムスタンプを表示
            layout.label(
                text=f"{item.object_name}: {item.name} ({item.timestamp})",
                icon="RECOVER_LAST",
            )
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon="RECOVER_LAST")

    def draw_filter(self, context, layout):
        """フィルタリングUI"""
        # 検索ボックス
        layout.prop(self, "filter_name", text="", icon="VIEWZOOM")

        # フィルタ切り替えボタン
        layout.prop(
            context.scene.history_manager,
            "filter_current_object",
            text="Current Object Only",
            toggle=True,
        )

    def filter_items(self, context, data, propname):
        """フィルタリング処理"""
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        # フィルタフラグを初期化（全て表示）
        flt_flags = [self.bitflag_filter_item] * len(items)
        flt_neworder = []

        # 現在のオブジェクトによるフィルタリング
        history_props = context.scene.history_manager
        if history_props.filter_current_object:
            if not context.active_object:
                # アクティブオブジェクトがない場合は全て非表示
                flt_flags = [0] * len(items)
            else:
                active_uuid = context.active_object.get("history_uuid")
                if not active_uuid:
                    # UUIDがない場合は全て非表示
                    flt_flags = [0] * len(items)
                else:
                    # 現在のオブジェクトの履歴のみ表示
                    for i, item in enumerate(items):
                        if item.object_uuid != active_uuid:
                            flt_flags[i] &= ~self.bitflag_filter_item

        # 名前によるフィルタリング（オブジェクトフィルタが適用された後）
        if self.filter_name:
            name_flags = helper_funcs.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item,
                items,
                "name",
                reverse=self.use_filter_sort_reverse,
            )
            # 両方のフィルタ条件を組み合わせ
            for i in range(len(flt_flags)):
                flt_flags[i] &= name_flags[i]

        # ソート処理（タイムスタンプ順）
        if self.use_filter_sort_alpha:
            flt_neworder = helper_funcs.sort_items_by_name(items, "timestamp")

        return flt_flags, flt_neworder


class HistoryManagerProperties(PropertyGroup):
    history_list: CollectionProperty(type=HistoryEntry)
    active_history_index: IntProperty(name="Active History Index", default=-1)
    max_history_count: IntProperty(
        name="Max History Count per Object",
        description="Maximum number of history entries to keep per object",
        default=10,
        min=1,
        max=50,
    )
    """
    auto_record: bpy.props.BoolProperty(
        name="Auto Record",
        description="Automatically record states during operations",
        default=False,
    )
    """
    filter_current_object: bpy.props.BoolProperty(
        name="Filter Current Object",
        description="Show only history entries for the current active object",
        default=False,
        update=lambda self, context: update_filter_display(context),
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
        box.prop(history_props, "filter_current_object")

        """
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
        """

        layout.separator()

        # アクティブオブジェクト情報
        if context.active_object:
            obj = context.active_object
            obj_uuid = obj.get("history_uuid", "Not assigned")
            layout.label(text=f"Active: {obj.name}")
            layout.label(
                text=(
                    f"UUID: {obj_uuid[:8]}..."
                    if len(obj_uuid) > 8
                    else f"UUID: {obj_uuid}"
                )
            )

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

        row = layout.row(align=True)
        row.operator("history.clear_object_history", text="Clear Object", icon="CANCEL")
        row.operator("history.clear_all", text="Clear All", icon="TRASH")

        # 情報表示
        if len(history_props.history_list) > 0:
            layout.separator()
            layout.label(text=f"Total entries: {len(history_props.history_list)}")

            # オブジェクトごとの統計
            obj_counts = {}
            for entry in history_props.history_list:
                obj_name = entry.object_name
                obj_counts[obj_name] = obj_counts.get(obj_name, 0) + 1

            if len(obj_counts) > 1:
                layout.label(text="Per object:")
                for obj_name, count in obj_counts.items():
                    layout.label(text=f"  {obj_name}: {count}")


# フィルタ表示更新用の関数
def update_filter_display(context):
    """フィルタ設定変更時にUIを更新"""
    # エリアの再描画を強制
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


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


# アクティブオブジェクト変更時のハンドラー
def active_object_handler(scene, depsgraph):
    """アクティブオブジェクト変更時にUIを更新"""
    history_props = scene.history_manager
    if history_props.filter_current_object:
        # フィルタが有効な場合のみUI更新
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


classes = [
    HistoryEntry,
    HistoryManagerProperties,
    HISTORY_OT_save_state,
    HISTORY_OT_restore_state,
    HISTORY_OT_delete_entry,
    HISTORY_OT_clear_all,
    HISTORY_OT_clear_object_history,
    # HISTORY_OT_auto_record_toggle,
    HISTORY_UL_list,
    VIEW3D_PT_history_manager,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.history_manager = bpy.props.PointerProperty(
        type=HistoryManagerProperties
    )

    # ハンドラーを登録
    if active_object_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(active_object_handler)


def unregister():
    # ハンドラーを削除
    if active_object_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(active_object_handler)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.history_manager


if __name__ == "__main__":
    register()
