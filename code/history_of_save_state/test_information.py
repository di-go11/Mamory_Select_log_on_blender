# test_history_operator.py
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

# テスト用のモッククラス
class MockBMeshVert:
    def __init__(self, x, y, z, index):
        self.co = Mock()
        self.co.x, self.co.y, self.co.z = x, y, z
        self.index = index

class MockBMeshEdge:
    def __init__(self, v1_idx, v2_idx):
        self.verts = [Mock(index=v1_idx), Mock(index=v2_idx)]

class MockBMeshFace:
    def __init__(self, vert_indices):
        self.verts = [Mock(index=i) for i in vert_indices]

class MockBMesh:
    def __init__(self):
        self.verts = [
            MockBMeshVert(0, 0, 0, 0),
            MockBMeshVert(1, 0, 0, 1),
            MockBMeshVert(1, 1, 0, 2),
            MockBMeshVert(0, 1, 0, 3)
        ]
        self.faces = [MockBMeshFace([0, 1, 2, 3])]
        self.edges = [
            MockBMeshEdge(0, 1),
            MockBMeshEdge(1, 2),
            MockBMeshEdge(2, 3),
            MockBMeshEdge(3, 0)
        ]
    
    def free(self):
        pass

class MockObject:
    def __init__(self):
        self.type = "MESH"
        self.data = Mock()
        self.location = (1.0, 2.0, 3.0)
        self.rotation_euler = (0.0, 0.0, 0.0)
        self.scale = (1.0, 1.0, 1.0)

class MockHistoryEntry:
    def __init__(self):
        self.name = ""
        self.timestamp = ""
        self.data = ""

class MockHistoryList:
    def __init__(self):
        self.entries = []
    
    def add(self):
        entry = MockHistoryEntry()
        self.entries.append(entry)
        return entry
    
    def remove(self, index):
        del self.entries[index]
    
    def __len__(self):
        return len(self.entries)

class MockHistoryProps:
    def __init__(self):
        self.history_list = MockHistoryList()
        self.max_history_count = 10

class MockScene:
    def __init__(self):
        self.history_manager = MockHistoryProps()

class MockContext:
    def __init__(self):
        self.scene = MockScene()
        self.active_object = MockObject()
