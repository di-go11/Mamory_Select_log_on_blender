import CreateLog

# addon imformation
bl_info = {
    "name": "SelectBack Addon",
    "author": "dgg",
    "version": (0, 1, 0),
    "blender": (4, 2, 3),
    "location": "View3D > Tool Shelf",
    "category": "3D View",
}

if __name__ == "__main__":
    CreateLog = CreateLog.CreateLog()
    log = CreateLog.Create()
    print(log)
