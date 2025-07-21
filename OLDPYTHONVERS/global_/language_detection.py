import os

def detect_language_by_extension(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".py":
        return "python"
    elif ext == ".java":
        return "java"
    elif ext in [".c", ".h"]:
        return "c"
    elif ext == ".js":
        return "javascript"
    elif ext == ".ts":
        return "typescript"
    elif ext == ".rb":
        return "ruby"
    elif ext == ".go":
        return "go"
    elif ext == ".swift":
        return "swift"
    elif ext == ".php":
        return "php"
    elif ext == ".rs":
        return "rust"
    elif ext == ".kt":
        return "kotlin"
    elif ext in [".sql"]:
        return "sql"
    elif ext in [".sh", ".bash"]:
        return "bash"
    # Add more as needed
    return "plain"