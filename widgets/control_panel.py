import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import os

class ControlPanel(tk.Frame):
    def __init__(self, parent, editor_ref, project_path=os.getcwd(), recent_files=None, **kwargs):
        super().__init__(parent, bg="#1f1f1f", **kwargs)
        self.editor_ref = editor_ref
        self.project_path = project_path
        self.recent_files = recent_files or []

        self.all_file_paths = []

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
        style.configure("TNotebook.Tab", background="#444", foreground="#ccc", padding=8)
        style.map("TNotebook.Tab", background=[("selected", "#1e90ff")])

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)

        self._build_project_tab()
        self._build_recent_tab()
        self._build_tools_tab()

    def _build_project_tab(self):
        project_frame = tk.Frame(self.tabs, bg="#1f1f1f")

        header = tk.Label(project_frame, text="📁 Project Explorer", bg="#1f1f1f", fg="#ffffff",
                          font=("Segoe UI", 11, "bold"))
        header.pack(padx=10, pady=(10, 0), anchor="w")

        search_frame = tk.Frame(project_frame, bg="#1f1f1f")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 10),
                                bg="#2b2b2b", fg="white", insertbackground="white", relief="flat")
        search_entry.pack(fill="x", expand=True, padx=10, pady=5)
        search_entry.bind("<KeyRelease>", self.filter_tree)
        search_frame.pack(fill="x")

        toolbar = tk.Frame(project_frame, bg="#1f1f1f")
        tk.Button(toolbar, text="➕ New File", command=self.create_new_file,
                  bg="#333", fg="white", relief="flat").pack(side="left", padx=5)
        tk.Button(toolbar, text="🖥️ Browse", command=self.browse_computer,
                  bg="#333", fg="white", relief="flat").pack(side="left", padx=5)
        toolbar.pack(fill="x", padx=10, pady=(0, 5))

        self.project_tree = ttk.Treeview(project_frame, selectmode="browse")
        self.project_tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=5)
        vsb = ttk.Scrollbar(project_frame, orient="vertical", command=self.project_tree.yview)
        self.project_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 10), pady=5)

        self.populate_tree(self.project_path)
        self.project_tree.bind("<Double-1>", self.open_selected_file)
        self.tabs.add(project_frame, text="Project")

    def filter_tree(self, event=None):
        query = self.search_var.get().lower()
        self.project_tree.delete(*self.project_tree.get_children())

        root_node = self.project_tree.insert("", "end", text=os.path.basename(self.project_path), open=True)
        for path in self.all_file_paths:
            filename = os.path.basename(path).lower()
            if query in filename:
                parent = self.project_tree.insert(root_node, "end", text=filename, values=[path])

    def _build_recent_tab(self):
        recent_frame = tk.Frame(self.tabs, bg="#1f1f1f")
        header = tk.Label(recent_frame, text="🕓 Recently Opened", bg="#1f1f1f", fg="#ffffff",
                          font=("Segoe UI", 11, "bold"))
        header.pack(padx=10, pady=(10, 5), anchor="w")

        self.recent_listbox = tk.Listbox(recent_frame, bg="#2a2a2a", fg="#ffffff",
                                         selectbackground="#3a3a3a", relief="flat",
                                         font=("Consolas", 10))
        self.recent_listbox.pack(fill="both", expand=True, padx=10, pady=5)

        for file in self.recent_files:
            self.recent_listbox.insert("end", file)

        self.tabs.add(recent_frame, text="Recent")

    def _build_tools_tab(self):
        tools_frame = tk.Frame(self.tabs, bg="#1f1f1f")
        header = tk.Label(tools_frame, text="🛠️ Tools Panel", bg="#1f1f1f", fg="#ffffff",
                          font=("Segoe UI", 11, "bold"))
        header.pack(padx=10, pady=(10, 5), anchor="w")

        tk.Label(tools_frame, text="Coming soon...", bg="#1f1f1f", fg="#aaaaaa").pack(pady=20)
        self.tabs.add(tools_frame, text="Tools")

    def populate_tree(self, path):
        self.project_tree.delete(*self.project_tree.get_children())
        self.all_file_paths.clear()
        root_node = self.project_tree.insert("", "end", text=os.path.basename(path), open=True)
        self._add_nodes(root_node, path)

    def _add_nodes(self, parent, path):
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                self.all_file_paths.append(item_path)
                node = self.project_tree.insert(parent, "end", text=item, values=[item_path])
                if os.path.isdir(item_path):
                    self._add_nodes(node, item_path)
        except PermissionError:
            pass

    def create_new_file(self):
        item = self.project_tree.selection()
        if not item:
            messagebox.showinfo("Info", "Please select a directory first")
            return

        path = self.project_tree.item(item[0], "values")[0]
        if not os.path.isdir(path):
            path = os.path.dirname(path)

        filename = simpledialog.askstring("New File", "Enter filename (with extension):")
        if filename:
            if "." not in filename:
                filename += ".txt"
            full_path = os.path.join(path, filename)
            try:
                open(full_path, "w").close()
                self.populate_tree(self.project_path)
            except Exception as e:
                messagebox.showerror("Error", f"Creation failed: {str(e)}")

    def browse_computer(self):
        paths = filedialog.askopenfilenames()
        if paths:
            for path in paths:
                self.editor_ref.open_file_in_tab(path)

    def open_selected_file(self, event):
        item = self.project_tree.selection()
        if item:
            path = self.project_tree.item(item[0], "values")[0]
            if os.path.isfile(path):
                self.editor_ref.open_file_in_tab(path)

    def add_recent_file(self, filepath):
        if filepath not in self.recent_files:
            self.recent_files.insert(0, filepath)
            if len(self.recent_files) > 10:
                self.recent_files = self.recent_files[:10]
            self.refresh_recent_list()

    def refresh_recent_list(self):
        self.recent_listbox.delete(0, "end")
        for file in self.recent_files:
            self.recent_listbox.insert("end", file)
