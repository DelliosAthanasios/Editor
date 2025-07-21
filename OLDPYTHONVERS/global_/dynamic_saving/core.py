import threading
import hashlib

class DynamicSaver:
    def __init__(self, save_interval_ms=2000):
        self.save_interval_ms = save_interval_ms
        self.last_saved_text = {}
        self.save_locks = {}
        self.save_threads = {}

    def should_save(self, editor_tab, text):
        last = self.last_saved_text.get(editor_tab)
        return last != text

    def mark_saved(self, editor_tab, text):
        self.last_saved_text[editor_tab] = text

    def save(self, editor_tab, file_path, text, on_error=None):
        # For large files, save in a background thread
        if len(text) > 2_000_000:  # ~2MB threshold for large files
            if editor_tab in self.save_threads and self.save_threads[editor_tab].is_alive():
                return  # Already saving
            lock = self.save_locks.setdefault(editor_tab, threading.Lock())
            def save_job():
                try:
                    with lock:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        self.mark_saved(editor_tab, text)
                except Exception as e:
                    if on_error:
                        on_error(e)
            t = threading.Thread(target=save_job, daemon=True)
            self.save_threads[editor_tab] = t
            t.start()
        else:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.mark_saved(editor_tab, text)
            except Exception as e:
                if on_error:
                    on_error(e) 