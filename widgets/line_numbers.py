import tkinter as tk

class LineNumbers(tk.Canvas):
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, width=40, bg="#2e2e2e", highlightthickness=0, **kwargs)
        self.text_widget = text_widget
        self.bind_events()
        self.redraw()

    def bind_events(self):
        events = ("<KeyRelease>", "<MouseWheel>", "<ButtonRelease-1>", "<Configure>", "<FocusIn>", "<Visibility>")
        for event in events:
            self.text_widget.bind(event, self.redraw)

    def redraw(self, event=None):
        self.after(10, self._redraw_internal)

    def _redraw_internal(self):
        if not self.winfo_exists():
            return  # Prevent redraw on destroyed widget
        self.delete("all")
        try:
            font_size = int(self.text_widget.cget("font").split()[-1])
        except:
            font_size = 12

        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(5, y, anchor="nw", text=linenum,
                             font=("Consolas", font_size), fill="#aaaaaa")
            i = self.text_widget.index(f"{i}+1line")


