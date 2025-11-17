import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import mounter

DOCKER_IMAGE = "lispmachine"
DOCKER_CONTAINER = "lispmachine"

if sys.platform == "win32":
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = 0

def run_subprocess(*args, **kwargs):
    if "creationflags" not in kwargs:
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return subprocess.run(*args, **kwargs)

def get_running_containers():
    result = run_subprocess(["docker", "ps", "--format", "{{.Names}}"], stdout=subprocess.PIPE, text=True)
    containers = result.stdout.strip().split('\n') if result.stdout else []
    return [c for c in containers if c]

class LispMachineCLI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lisp Machine CLI Manager")
        self.geometry("900x500")
        self.create_menu()
        self.create_cli()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_menu(self):
        menubar = tk.Menu(self)
        mount_menu = tk.Menu(menubar, tearoff=0)
        mount_menu.add_command(label="Manage Mounting Folders", command=self.open_mount_dialog)
        menubar.add_cascade(label="Mount", menu=mount_menu)
        machines_menu = tk.Menu(menubar, tearoff=0)
        machines_menu.add_command(label="List Running Machines", command=self.list_running_machines)
        menubar.add_cascade(label="Machines", menu=machines_menu)
        self.config(menu=menubar)

    def create_cli(self):
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=1)
        self.terminal = tk.Text(frame, bg="black", fg="white", height=20, wrap=tk.NONE)
        self.terminal.pack(fill=tk.BOTH, expand=1)
        cmd_frame = ttk.Frame(frame)
        cmd_frame.pack(fill=tk.X)
        self.cmd_entry = tk.Entry(cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=1)
        self.cmd_entry.bind("<Return>", self.send_command_to_container)
        send_btn = tk.Button(cmd_frame, text="Send", command=self.send_command_to_container)
        send_btn.pack(side=tk.RIGHT)

    def send_command_to_container(self, event=None):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        self.terminal.insert(tk.END, f"$ {cmd}\n")
        self.terminal.see(tk.END)
        self.cmd_entry.delete(0, tk.END)
        try:
            proc = subprocess.Popen(
                ["docker", "exec", DOCKER_CONTAINER, "bash", "-c", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            stdout, stderr = proc.communicate()
            if stdout:
                self.terminal.insert(tk.END, stdout)
            if stderr:
                self.terminal.insert(tk.END, stderr)
            self.terminal.see(tk.END)
        except Exception as e:
            self.terminal.insert(tk.END, f"Error: {e}\n")
            self.terminal.see(tk.END)

    def open_mount_dialog(self):
        mounter.mount_dialog(self)

    def list_running_machines(self):
        machines = get_running_containers()
        messagebox.showinfo("Running Machines", "\n".join(machines) if machines else "None running.")

    def on_close(self):
        running = get_running_containers()
        if running:
            msg = "Closing container(s):\n" + "\n".join(running)
            messagebox.showinfo("Exit", msg)
            for c in running:
                run_subprocess(["docker", "kill", c], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.destroy()

if __name__ == "__main__":
    # Ensure the container is running (or create it)
    from mounter import ensure_container_running
    ensure_container_running(DOCKER_IMAGE, DOCKER_CONTAINER)
    app = LispMachineCLI()
    app.mainloop()
