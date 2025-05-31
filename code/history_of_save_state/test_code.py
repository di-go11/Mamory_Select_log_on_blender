import bpy
import bmesh
from test_information import MockBPyTypesObject, MockContext
import unittest
from history_ot_save_state import HISTORY_OT_save_state

class TestHISTORY_OT_save_state(unittest.TestCase):

    def setUp(self):
        # 各テストの前に実行されるセットアップ
        self.operator = HISTORY_OT_save_state()
        self.context = MockContext()
        
        # report メソッドをモックして、メッセージが正しく報告されるかを確認できるようにする
        self.operator.report = unittest.mock.Mock()

        # bpy.ops.object.mode_set が呼ばれた回数をリセット
        bpy.ops.object.mode_set.reset_mock()
        bmesh.from_mesh.reset_mock()

    def test_execute_with_mesh_object(self):
        """メッシュオブジェクトが選択されている場合の実行テスト"""
        mesh_obj = MockBPyTypesObject("MyMesh", "MESH")
        self.context.active_object = mesh_obj

        result = self.operator.execute(self.context)

        # 戻り値の確認
        self.assertEqual(result, {"FINISHED"})

        # history_list にエントリが追加されたか確認
        self.assertEqual(len(self.context.scene.history_manager.history_list), 1)
        added_entry = self.context.scene.history_manager.history_list._items[0]

        # エントリのデータが正しく保存されたか確認
        self.assertIn("vertices", json.loads(added_entry.data))
        self.assertIn("location", json.loads(added_entry.data))

        # report が 'INFO' で呼び出されたか確認
        self.operator.report.assert_called_with({"INFO"}, unittest.mock.ANY)
        self.assertIn("State saved:", self.operator.report.call_args[0][1])

        # serialize_mesh が呼び出されたか確認
        # このテストは serialize_mesh 内の bpy.ops.object.mode_set の呼び出しも確認します
        bpy.ops.object.mode_set.assert_any_call(mode="EDIT")
        bpy.ops.object.mode_set.assert_any_call(mode="OBJECT")
        self.assertEqual(bpy.ops.object.mode_set.call_count, 2)
        bmesh.from_mesh.assert_called_once()


    def test_execute_without_mesh_object(self):
        """メッシュオブジェクトが選択されていない場合の実行テスト"""
        self.context.active_object = MockBPyTypesObject("EmptyObject", "EMPTY") # 非メッシュオブジェクト

        result = self.operator.execute(self.context)

        # 戻り値の確認
        self.assertEqual(result, {"FINISHED"})

        # history_list に何も追加されていないか確認
        self.assertEqual(len(self.context.scene.history_manager.history_list), 0)

        # report が 'WARNING' で呼び出されたか確認
        self.operator.report.assert_called_with({"WARNING"}, "No mesh object selected")

        # serialize_mesh が呼び出されていないか確認
        bpy.ops.object.mode_set.assert_not_called()
        bmesh.from_mesh.assert_not_called()

    def test_max_history_count_limit(self):
        """履歴の最大記録数制限のテスト"""
        self.context.scene.history_manager.max_history_count = 3
        mesh_obj = MockBPyTypesObject("Mesh", "MESH")
        self.context.active_object = mesh_obj

        # 5回保存を試みる
        for i in range(5):
            self.operator.execute(self.context)
        
        # 履歴リストの長さが max_history_count を超えないことを確認
        self.assertEqual(len(self.context.scene.history_manager.history_list), 3)

        # 最初の2つのエントリが削除されたことを確認（FIFO）
        # モックの `entry.name` が自動で State 1, State 2... となることを期待する
        # このテストでは、`entry.name` を使って、リストの順序が正しく維持されていることを確認する。
        # 新しいエントリが State 4, State 5 となり、それらがリストに残っていることを確認する。
        # _items[0] の name が State 3 になっているはず
        remaining_names = [e.name for e in self.context.scene.history_manager.history_list._items]
        self.assertIn("State 3", remaining_names)
        self.assertIn("State 4", remaining_names)
        self.assertIn("State 5", remaining_names) # 実際に保存されたのが 1,2,3,4,5 で、1,2が削除され3,4,5が残る
        
        # モックの `history_list.add()` は新しいオブジェクトを返すので、
        # `entry.name` は `len(history_props.history_list)` の時点での長さに依存する。
        # したがって、ループの順序で `State 1` から `State 5` が生成される。
        # `remove(0)` が2回呼び出されることで `State 1` と `State 2` が削除され、
        # 結果として `State 3`, `State 4`, `State 5` が残る。

    def test_serialize_mesh_data_structure(self):
        """serialize_mesh メソッドが正しい構造のデータを返すかテスト"""
        mesh_obj = MockBPyTypesObject("TestMesh", "MESH")
        # bmesh.from_mesh のモックがダミーデータを提供するため、ここでは特別な設定は不要
        
        mesh_data = self.operator.serialize_mesh(mesh_obj)

        self.assertIn("vertices", mesh_data)
        self.assertIn("faces", mesh_data)
        self.assertIn("edges", mesh_data)
        self.assertIn("location", mesh_data)
        self.assertIn("rotation", mesh_data)
        self.assertIn("scale", mesh_data)

        self.assertIsInstance(mesh_data["vertices"], list)
        self.assertIsInstance(mesh_data["faces"], list)
        self.assertIsInstance(mesh_data["edges"], list)
        self.assertIsInstance(mesh_data["location"], list)
        self.assertIsInstance(mesh_data["rotation"], list)
        self.assertIsInstance(mesh_data["scale"], list)

        # bpy.ops.object.mode_set が正しく呼び出されたことを確認
        bpy.ops.object.mode_set.assert_any_call(mode="EDIT")
        bpy.ops.object.mode_set.assert_any_call(mode="OBJECT")
        self.assertEqual(bpy.ops.object.mode_set.call_count, 2)
        bmesh.from_mesh.assert_called_once()