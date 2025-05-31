import unittest
import unittest.mock


# --- Blenderのダミーモジュールとクラス ---
# テストのためにbpyとbmeshの基本的な構造をモックアップします
class MockBPyTypesOperator:
    bl_idname = ""
    bl_label = ""
    bl_description = ""
    bl_options = set()

    def execute(self, context):
        raise NotImplementedError


class MockBPyTypesMesh:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.edges = []
        self.name = "MockMesh"


class MockBPyTypesObject:
    def __init__(self, name="Object", obj_type="MESH"):
        self.name = name
        self.type = obj_type
        self.data = MockBPyTypesMesh()  # メッシュデータ
        self.location = [0.0, 0.0, 0.0]
        self.rotation_euler = [0.0, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]


class MockCollection:
    def __init__(self):
        self._items = []
        self._index = 0

    def add(self):
        item = unittest.mock.Mock()
        self._items.append(item)
        return item

    def remove(self, index):
        if 0 <= index < len(self._items):
            del self._items[index]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return self

    def __next__(self):
        if self._index < len(self._items):
            item = self._items[self._index]
            self._index += 1
            return item
        else:
            self._index = 0  # Reset for next iteration
            raise StopIteration


class MockHistoryManager:
    def __init__(self):
        self.history_list = MockCollection()
        self.max_history_count = 5


class MockScene:
    def __init__(self):
        self.history_manager = MockHistoryManager()


class MockContext:
    def __init__(self):
        self.active_object = None
        self.scene = MockScene()
        self.view_layer = unittest.mock.Mock()
        self.view_layer.objects.active = (
            None  # activeオブジェクトをセットできるようにモック
        )


class MockBmeshVert:
    def __init__(self, co, index):
        self.co = co
        self.index = index


class MockBmeshFace:
    def __init__(self, verts):
        self.verts = verts


class MockBmeshEdge:
    def __init__(self, verts):
        self.verts = verts


class MockBmesh:
    def __init__(self, verts_data, faces_data, edges_data):
        self.verts = [MockBmeshVert(v, i) for i, v in enumerate(verts_data)]
        self.faces = []
        for face_indices in faces_data:
            self.faces.append(MockBmeshFace([self.verts[i] for i in face_indices]))
        self.edges = []
        for edge_indices in edges_data:
            self.edges.append(
                MockBmeshEdge(
                    [self.verts[edge_indices[0]], self.verts[edge_indices[1]]]
                )
            )

    def free(self):
        pass  # ダミーなので何もしない


# bpyモジュールとbmeshモジュールのモック
bpy = unittest.mock.Mock()
bpy.types = unittest.mock.Mock()
bpy.types.Operator = MockBPyTypesOperator  # オペレーターの基底クラスを設定
bpy.ops = unittest.mock.Mock()
bpy.ops.object = unittest.mock.Mock()  # bpy.ops.object.mode_set をモックするため

bmesh = unittest.mock.Mock()
bmesh.from_mesh = unittest.mock.Mock(
    side_effect=lambda mesh_data: MockBmesh(
        verts_data=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)],  # ダミーの頂点データ
        faces_data=[[0, 1, 2, 3]],  # ダミーの面データ
        edges_data=[(0, 1), (1, 3), (3, 2), (2, 0)],  # ダミーのエッジデータ
    )
)
