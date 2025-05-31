from bpy.types import Operator
import bpy
import time
import bmesh
import json
import test_code

#class HISTORY_OT_save_state(Operator):
class HISTORY_OT_save_state(test_code.MockBPyTypesOperator):
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

        return {"FINISHED"}

    def serialize_mesh(self, obj):
        """メッシュオブジェクトをシリアライズ"""
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        bm = bmesh.from_mesh(obj.data)

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
