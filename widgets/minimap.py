import tkinter as tk

class Minimap(tk.Canvas):
    def __init__(self, parent, text_widget, linenumbers=None, **kwargs):
        super().__init__(parent, width=100, bg="#2e2e2e", highlightthickness=0, **kwargs)
        self.text_widget = text_widget
        self.linenumbers = linenumbers
        self.font_name = "Courier New"
        self.font_size = 6
        self.line_spacing = 9
        self.max_line_length = 50

        self.after_id = None
        self.last_y = 0

        self.bind("<Button-1>", self.scroll_to_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<MouseWheel>", self.on_mousewheel)

        self.text_widget.bind("<KeyRelease>", lambda e: self.schedule_update())
        self.text_widget.bind("<MouseWheel>", lambda e: self.schedule_update())
        self.text_widget.bind("<ButtonRelease-1>", lambda e: self.schedule_update())
        self.text_widget.bind("<<Modified>>", lambda e: self.schedule_update())
        self.text_widget.bind("<Configure>", lambda e: self.schedule_update())

    def schedule_update(self, event=None):
        if self.after_id:
            self.after_cancel(self.after_id)
        self.after_id = self.after(50, self.update_minimap)

    def update_minimap(self):
        self.delete("all")
        height = self.winfo_height()
        total_lines = int(self.text_widget.index("end-1c").split('.')[0])
        lines_to_render = int(height / self.line_spacing)

        first_visible = int(self.text_widget.index("@0,0").split('.')[0])
        last_visible = min(first_visible + lines_to_render, total_lines)

        for idx in range(first_visible, last_visible):
            y_pos = (idx - first_visible) * self.line_spacing
            line = self.text_widget.get(f"{idx + 1}.0", f"{idx + 1}.end")
            line = line.replace('\t', '    ')[:self.max_line_length]
            self.create_text(2, y_pos, anchor="nw", text=line,
                             fill="#909090", font=(self.font_name, self.font_size))

        if self.linenumbers and self.linenumbers.winfo_exists():
            self.linenumbers.redraw()

        self.after_id = None

    def scroll_to_click(self, event):
        total_lines = int(self.text_widget.index("end-1c").split('.')[0])
        rel_y = event.y / self.winfo_height()
        target_line = max(1, min(int(rel_y * total_lines), total_lines))
        self.text_widget.see(f"{target_line}.0")
        self.last_y = event.y
        self.schedule_update()

    def on_drag(self, event):
        delta = (event.y - self.last_y) * 2
        self.text_widget.yview_scroll(int(-delta), "units")
        self.last_y = event.y
        self.schedule_update()

    def on_mousewheel(self, event):
        direction = -1 if event.delta > 0 else 1
        self.text_widget.yview_scroll(direction, "units")
        self.schedule_update()




