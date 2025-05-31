from abc import ABC, abstractmethod
import bpy
import bmesh


class InterfaceCreateLog(ABC):
    @abstractmethod
    def Create(self):
        pass

class CreateLog(InterfaceCreateLog):

    def __init__(self):
        self.obj = bpy.context.active_object  # 選択中のオブジェクトを格納
        self.me = self.obj.data  # メッシュデータを格納
        self.bm = bmesh.from_edit_mesh(self.me)

    def Create(self):
        # 選択中の頂点取得
        selected_verts = [v for v in self.bm.verts if v.select]

        """
        # わーるだ座標で出力
        for vertspoint in selected_verts:
            print(f"vertex:座標{vertspoint.co.x},{vertspoint.co.y},{vertspoint.co.z}\n")
            print(f"vertexインデックス{vertspoint.index}\n")
        """
        return selected_verts