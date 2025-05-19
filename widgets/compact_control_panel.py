import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import os

class CompactControlPanel(tk.Frame):
    def __init__(self, master, editor_ref, start_path=os.getcwd(), **kwargs):
        super().__init__(master, bg="#1e1e1e", **kwargs)
        self.editor_ref = editor_ref
        self.start_path = start_path
        self.all_file_paths = []

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        rowheight=22,
                        font=("Segoe UI", 10))
        style.map("Treeview",
                  background=[("selected", "#3c3f41")],
                  foreground=[("selected", "white")])

        self.paned = ttk.Panedwindow(self, orient="vertical")
        self.paned.pack(fill="both", expand=True)

        top_frame = tk.Frame(self.paned, bg="#1e1e1e")

        # Search bar
        search_frame = tk.Frame(top_frame, bg="#1e1e1e")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 9),
                                bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        search_entry.pack(fill="x", expand=True, padx=5, pady=5)
        search_entry.bind("<KeyRelease>", self.filter_tree)
        search_frame.pack(fill="x")

        # Path label
        self.path_label = tk.Label(top_frame, text=self.start_path, anchor="w", bg="#1e1e1e", fg="white",
                                   font=("Segoe UI", 9))
        self.path_label.pack(fill="x", padx=5)

        # Treeview for file explorer
        self.tree = ttk.Treeview(top_frame)
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(top_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        bottom_frame = tk.Frame(self.paned, bg="#1e1e1e")
        self.new_file_btn = tk.Button(bottom_frame, text="＋ New File",
                                      font=("Segoe UI", 10, "bold"),
                                      bg="#444", fg="white",
                                      relief="flat", cursor="hand2",
                                      activebackground="#555",
                                      command=self.create_new_file)
        self.new_file_btn.pack(padx=10, pady=(8, 4), anchor="center")

        self.root_btn = tk.Button(bottom_frame, text="📂 Root", font=("Segoe UI", 10),
                                  bg="#444", fg="white", relief="flat", cursor="hand2",
                                  activebackground="#555", command=self.go_to_root)
        self.root_btn.pack(padx=10, pady=(4, 10), anchor="center")

        self.paned.add(top_frame, weight=8)
        self.paned.add(bottom_frame, weight=1)

        self.populate_tree(self.start_path)
        self.tree.bind("<Double-1>", self.open_file_from_tree)

    def populate_tree(self, path):
        self.start_path = path
        self.path_label.config(text=path)
        self.tree.delete(*self.tree.get_children())
        self.all_file_paths.clear()
        root_node = self.tree.insert("", "end", text=os.path.basename(path), open=True, values=[path])
        self._add_nodes(root_node, path)

    def _add_nodes(self, parent, path):
        try:
            for item in sorted(os.listdir(path)):
                full_path = os.path.join(path, item)
                node = self.tree.insert(parent, "end", text=item, values=[full_path])
                self.all_file_paths.append((node, full_path))
                if os.path.isdir(full_path):
                    self.tree.insert(node, "end", text="Loading...", values=["dummy"])
        except PermissionError:
            pass

    def filter_tree(self, event=None):
        query = self.search_var.get().lower()
        for node, path in self.all_file_paths:
            filename = os.path.basename(path).lower()
            visible = query in filename if query else True
            try:
                self.tree.detach(node)
                if visible:
                    self.tree.reattach(node, self.tree.parent(node), "end")
            except tk.TclError:
                pass

    def open_file_from_tree(self, event):
        item = self.tree.selection()
        if not item:
            return

        node = item[0]
        path = self.tree.item(node, "values")[0]

        if path == "dummy":
            return

        if os.path.isdir(path):
            if not self.tree.get_children(node):
                self.tree.delete(*self.tree.get_children(node))
                self._add_nodes(node, path)
            else:
                self.tree.item(node, open=not self.tree.item(node, "open"))
        elif os.path.isfile(path):
            self.editor_ref.open_file_in_tab(path)

    def create_new_file(self):
        item = self.tree.selection()
        if not item:
            messagebox.showinfo("No selection", "Please select a folder.")
            return

        folder_path = self.tree.item(item[0], "values")[0]
        if not os.path.isdir(folder_path):
            folder_path = os.path.dirname(folder_path)

        filename = simpledialog.askstring("New File", "Enter new filename:")
        if filename:
            full_path = os.path.join(folder_path, filename)
            try:
                with open(full_path, "w") as f:
                    f.write("")
                messagebox.showinfo("File Created", f"Created: {full_path}")
                self.populate_tree(self.start_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create file:\n{e}")

    def go_to_root(self):
        self.populate_tree(os.path.abspath(os.sep))


