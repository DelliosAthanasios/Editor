def on_save(editor, file_path):
    print(f"File {file_path} was saved! (from user plugin)")
    # Custom logic here

def register(api):
    api.register_hook('on_save', on_save) 