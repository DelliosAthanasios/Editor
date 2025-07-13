import hashlib

def hash_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def write_file_atomic(file_path, text):
    # Write to a temp file and move to avoid partial writes
    import os, tempfile, shutil
    dir_name = os.path.dirname(file_path)
    with tempfile.NamedTemporaryFile('w', delete=False, dir=dir_name, encoding='utf-8') as tf:
        tf.write(text)
        tempname = tf.name
    shutil.move(tempname, file_path)

def chunked_write(file_path, text, chunk_size=1024*1024):
    # Write large files in chunks
    with open(file_path, 'w', encoding='utf-8') as f:
        for i in range(0, len(text), chunk_size):
            f.write(text[i:i+chunk_size]) 