from bpy.props import StringProperty
from bpy.types import PropertyGroup

class HistoryEntry(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Name of this history entry",
        default="History Point"
    )
    
    timestamp: StringProperty(
        name="Timestamp",
        description="When this entry was created",
        default=""
    )
    
    data: StringProperty(
        name="Data",
        description="Serialized object data",
        default=""
    )