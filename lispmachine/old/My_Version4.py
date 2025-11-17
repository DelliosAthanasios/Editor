import subprocess
import os
import yaml
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

DOCKER_IMAGE = "lispmachine"
DOCKER_CONTAINER = "lispmachine"
DOCKERFILE_NAME = "Dockerfile"
DOCKER_COMPOSE_FILE = "docker-compose.yml"

def build_and_run_docker():
    if not os.path.isfile(DOCKERFILE_NAME):
        messagebox.showerror("Critical Error", "Dockerfile does not exist")
        return False

    build_proc = subprocess.run(
        ["docker", "build", "-t", DOCKER_IMAGE, "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if build_proc.returncode != 0:
        messagebox.showerror("Docker Build Failed", build_proc.stderr)
        return False

    # Remove existing container if it exists
    subprocess.run(["docker", "rm", "-f", DOCKER_CONTAINER], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Run docker container
    run_proc = subprocess.run(
        ["docker", "run", "--name", DOCKER_CONTAINER, "-dit", DOCKER_IMAGE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if run_proc.returncode != 0:
        messagebox.showerror("Docker Run Failed", run_proc.stderr)
        return False
    return True

def get_running_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE, text=True
        )
        containers = result.stdout.strip().split('\n') if result.stdout else []
        return [c for c in containers if c]
    except Exception as e:
        return []

class MountDialog(simpledialog.Dialog):
    def body(self, master):
        self.containers = get_running_containers()
        tk.Label(master, text="Select Container:").grid(row=0, column=0, sticky="w")
        self.container_var = tk.StringVar(value=self.containers[0] if self.containers else "")
        self.container_menu = ttk.Combobox(master, textvariable=self.container_var, values=self.containers, state='readonly')
        self.container_menu.grid(row=0, column=1, sticky="ew")

        tk.Label(master, text="Host Folder:").grid(row=1, column=0, sticky="w")
        self.host_folder_var = tk.StringVar()
        self.host_folder_entry = tk.Entry(master, textvariable=self.host_folder_var, width=40)
        self.host_folder_entry.grid(row=1, column=1, sticky="ew")
        self.browse_btn = tk.Button(master, text="Browse...", command=self.browse_folder)
        self.browse_btn.grid(row=1, column=2, sticky="w")

        tk.Label(master, text="Mount Point in Container:").grid(row=2, column=0, sticky="w")
        self.container_path_var = tk.StringVar(value="/mnt/shared")
        self.container_path_entry = tk.Entry(master, textvariable=self.container_path_var, width=40)
        self.container_path_entry.grid(row=2, column=1, sticky="ew")

        self.readonly_var = tk.BooleanVar()
        self.readonly_check = tk.Checkbutton(master, text="Read Only", variable=self.readonly_var)
        self.readonly_check.grid(row=3, column=1, sticky="w")

        return self.container_menu

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.host_folder_var.set(folder)

    def apply(self):
        self.result = {
            "container": self.container_var.get(),
            "host_folder": self.host_folder_var.get(),
            "mount_point": self.container_path_var.get(),
            "readonly": self.readonly_var.get()
        }

def update_docker_compose_with_mount(mount_info):
    compose_data = {}
    # Load existing compose file if present
    if os.path.exists(DOCKER_COMPOSE_FILE):
        with open(DOCKER_COMPOSE_FILE, "r") as f:
            compose_data = yaml.safe_load(f) or {}

    if "services" not in compose_data:
        compose_data["services"] = {}

    if DOCKER_CONTAINER not in compose_data["services"]:
        compose_data["services"][DOCKER_CONTAINER] = {
            "image": DOCKER_IMAGE,
            "container_name": DOCKER_CONTAINER,
            "volumes": []
        }

    service = compose_data["services"][DOCKER_CONTAINER]
    if "volumes" not in service:
        service["volumes"] = []

    # Remove any existing volume with the same mount point
    service["volumes"] = [
        v for v in service["volumes"]
        if not (isinstance(v, str) and v.endswith(mount_info["mount_point"]))
    ]

    vol_flag = f"{mount_info['host_folder']}:{mount_info['mount_point']}"
    if mount_info['readonly']:
        vol_flag += ":ro"

    service["volumes"].append(vol_flag)

    # Save changes
    with open(DOCKER_COMPOSE_FILE, "w") as f:
        yaml.dump(compose_data, f, default_flow_style=False)

class LispMachineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lisp Machine Manager")
        self.geometry("1000x600")
        self.create_menu()
        self.create_panes()

    def create_menu(self):
        menubar = tk.Menu(self)
        machines_menu = tk.Menu(menubar, tearoff=0)
        machines_menu.add_command(label="List Running Machines", command=self.list_running_machines)
        menubar.add_cascade(label="Machines", menu=machines_menu)

        mount_menu = tk.Menu(menubar, tearoff=0)
        mount_menu.add_command(label="Manage Mounting Folders", command=self.manage_mounting_folders)
        menubar.add_cascade(label="Mount", menu=mount_menu)

        self.config(menu=menubar)

    def create_panes(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=1)
        left_frame = ttk.Frame(paned)
        self.editor = tk.Text(left_frame)
        self.editor.pack(fill=tk.BOTH, expand=1)
        paned.add(left_frame, weight=1)
        right_frame = ttk.Frame(paned)
        # Terminal Output
        terminal_frame = ttk.Frame(right_frame)
        terminal_frame.pack(fill=tk.BOTH, expand=1)
        self.terminal = tk.Text(terminal_frame, bg="black", fg="white", height=20)
        self.terminal.pack(fill=tk.BOTH, expand=1)

        # Real-time command entry
        cmd_frame = ttk.Frame(right_frame)
        cmd_frame.pack(fill=tk.X)
        self.cmd_entry = tk.Entry(cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=1)
        self.cmd_entry.bind("<Return>", self.send_command_to_container)
        send_btn = tk.Button(cmd_frame, text="Send", command=self.send_command_to_container)
        send_btn.pack(side=tk.RIGHT)
        paned.add(right_frame, weight=1)

    def list_running_machines(self):
        machines = get_running_containers()
        messagebox.showinfo("Running Machines", "\n".join(machines) if machines else "None running.")

    def manage_mounting_folders(self):
        dlg = MountDialog(self)
        if dlg.result:
            self.mount_folder_on_container(dlg.result)
            update_docker_compose_with_mount(dlg.result)

    def mount_folder_on_container(self, mount_info):
        container = mount_info["container"]
        source = mount_info["host_folder"]
        target = mount_info["mount_point"]
        readonly = mount_info["readonly"]

        if not container or not source or not target:
            messagebox.showerror("Error", "All fields must be filled.")
            return

        # Stop and remove the old container and run a new one with volume
        subprocess.run(["docker", "stop", container], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["docker", "rm", container], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        vol_flag = f"{source}:{target}"
        if readonly:
            vol_flag += ":ro"

        run_cmd = [
            "docker", "run", "--name", container, "-dit", "-v", vol_flag, DOCKER_IMAGE
        ]
        run_proc = subprocess.run(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if run_proc.returncode == 0:
            messagebox.showinfo("Success", f"Mounted {source} to {target} ({'read-only' if readonly else 'rw'}) in {container}.")
        else:
            messagebox.showerror("Docker Error", run_proc.stderr)

    def send_command_to_container(self, event=None):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        self.terminal.insert(tk.END, f"$ {cmd}\n")
        self.terminal.see(tk.END)
        self.cmd_entry.delete(0, tk.END)
        # Run docker exec
        try:
            proc = subprocess.Popen(
                ["docker", "exec", DOCKER_CONTAINER, "bash", "-c", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
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

if __name__ == "__main__":
    if build_and_run_docker():
        app = LispMachineGUI()
        app.mainloop()