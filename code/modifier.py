import bpy

def print_all_modifier_properties(obj=None):
    """オブジェクトの全モディファイアーの全プロパティを出力"""
    
    if obj is None:
        obj = bpy.context.active_object
    
    if obj is None:
        print("オブジェクトが選択されていません")
        return
    
    print(f"オブジェクト名: {obj.name}")
    print(f"モディファイアー数: {len(obj.modifiers)}")
    print("=" * 60)
    
    for i, modifier in enumerate(obj.modifiers):
        print(f"\n[{i+1}] モディファイアー名: {modifier.name}")
        print(f"タイプ: {modifier.type}")
        print("-" * 40)
        
        # 全プロパティを取得・出力
        for prop in modifier.bl_rna.properties:
            prop_name = prop.identifier
            
            # システムプロパティをスキップ
            if prop_name in ['rna_type', 'bl_rna']:
                continue
            
            try:
                value = getattr(modifier, prop_name)
                
                # データ型に応じて表示を調整
                if isinstance(value, (int, float, str, bool)):
                    print(f"  {prop_name}: {value}")
                elif hasattr(value, '__len__') and not isinstance(value, str):
                    # リスト、タプル、配列など
                    if len(value) <= 10:  # 短い配列は全て表示
                        print(f"  {prop_name}: {list(value)}")
                    else:  # 長い配列は一部のみ表示
                        print(f"  {prop_name}: {list(value[:5])}... (length: {len(value)})")
                elif hasattr(value, 'name'):
                    # Blenderオブジェクトの場合
                    print(f"  {prop_name}: {value.name}")
                else:
                    print(f"  {prop_name}: {str(value)}")
                    
            except Exception as e:
                print(f"  {prop_name}: [取得エラー: {str(e)}]")

def print_modifier_properties_detailed(obj=None):
    """より詳細な情報付きでモディファイアープロパティを出力"""
    
    if obj is None:
        obj = bpy.context.active_object
    
    if obj is None:
        print("オブジェクトが選択されていません")
        return
    
    print(f"オブジェクト名: {obj.name}")
    print(f"モディファイアー数: {len(obj.modifiers)}")
    print("=" * 80)
    
    for i, modifier in enumerate(obj.modifiers):
        print(f"\n[{i+1}] モディファイアー: {modifier.name} ({modifier.type})")
        print("-" * 60)
        
        # プロパティを分類して表示
        basic_props = []
        vector_props = []
        object_props = []
        other_props = []
        
        for prop in modifier.bl_rna.properties:
            prop_name = prop.identifier
            
            if prop_name in ['rna_type', 'bl_rna']:
                continue
            
            try:
                value = getattr(modifier, prop_name)
                prop_info = {
                    'name': prop_name,
                    'value': value,
                    'type': prop.type,
                    'description': getattr(prop, 'description', '説明なし')
                }
                
                if isinstance(value, (int, float, str, bool)):
                    basic_props.append(prop_info)
                elif hasattr(value, '__len__') and not isinstance(value, str):
                    vector_props.append(prop_info)
                elif hasattr(value, 'name'):
                    object_props.append(prop_info)
                else:
                    other_props.append(prop_info)
                    
            except Exception as e:
                other_props.append({
                    'name': prop_name,
                    'value': f'[エラー: {str(e)}]',
                    'type': 'ERROR',
                    'description': 'プロパティ取得に失敗'
                })
        
        # 分類別に表示
        if basic_props:
            print("  【基本プロパティ】")
            for prop in basic_props:
                print(f"    {prop['name']}: {prop['value']} ({prop['type']})")
                if prop['description'] != '説明なし':
                    print(f"      -> {prop['description']}")
        
        if vector_props:
            print("  【配列・ベクタープロパティ】")
            for prop in vector_props:
                if hasattr(prop['value'], '__len__') and len(prop['value']) <= 10:
                    print(f"    {prop['name']}: {list(prop['value'])} ({prop['type']})")
                else:
                    print(f"    {prop['name']}: [長さ {len(prop['value'])}の配列] ({prop['type']})")
        
        if object_props:
            print("  【オブジェクト参照プロパティ】")
            for prop in object_props:
                print(f"    {prop['name']}: {prop['value'].name} ({prop['type']})")
        
        if other_props:
            print("  【その他のプロパティ】")
            for prop in other_props:
                print(f"    {prop['name']}: {prop['value']} ({prop['type']})")

def export_all_modifiers_to_file(filepath=None, obj=None):
    """全モディファイアー情報をファイルに出力"""
    
    if obj is None:
        obj = bpy.context.active_object
    
    if obj is None:
        print("オブジェクトが選択されていません")
        return
    
    if filepath is None:
        filepath = bpy.path.abspath("//") + f"{obj.name}_all_modifiers.txt"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"オブジェクト名: {obj.name}\n")
        f.write(f"モディファイアー数: {len(obj.modifiers)}\n")
        f.write("=" * 80 + "\n")
        
        for i, modifier in enumerate(obj.modifiers):
            f.write(f"\n[{i+1}] モディファイアー: {modifier.name} ({modifier.type})\n")
            f.write("-" * 60 + "\n")
            
            for prop in modifier.bl_rna.properties:
                prop_name = prop.identifier
                
                if prop_name in ['rna_type', 'bl_rna']:
                    continue
                
                try:
                    value = getattr(modifier, prop_name)
                    f.write(f"{prop_name}: {value}\n")
                except Exception as e:
                    f.write(f"{prop_name}: [エラー: {str(e)}]\n")
    
    print(f"全モディファイアー情報を保存しました: {filepath}")

def get_modifier_property_names(modifier_type):
    """特定のモディファイアータイプで利用可能なプロパティ名を取得"""
    
    # 一時的なオブジェクトとモディファイアーを作成
    import bmesh
    
    mesh = bpy.data.meshes.new("temp_mesh")
    obj = bpy.data.objects.new("temp_obj", mesh)
    
    try:
        modifier = obj.modifiers.new("temp_mod", modifier_type)
        properties = [prop.identifier for prop in modifier.bl_rna.properties 
                     if prop.identifier not in ['rna_type', 'bl_rna']]
        
        # クリーンアップ
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)
        
        return properties
    except:
        # クリーンアップ
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj)
        if mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        return []

# 使用例
if __name__ == "__main__":
    # 基本的な全プロパティ出力
    print_all_modifier_properties()
    
    # 詳細情報付き出力
    # print_modifier_properties_detailed()
    
    # ファイルに出力
    # export_all_modifiers_to_file()
    
    # 特定のモディファイアータイプのプロパティ一覧を取得
    # print("SUBSURFモディファイアーのプロパティ:")
    # print(get_modifier_property_names('SUBSURF'))