import os
import subprocess
import sys
import yaml
from tkinter import simpledialog, filedialog, messagebox, Tk, Label, Entry, StringVar, BooleanVar, Checkbutton, Button
from tkinter.ttk import Combobox
DOCKER_COMPOSE_FILE = "docker-compose.yml"

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

def ensure_container_running(image, container):
    # Try to start or create the container if not running
    result = run_subprocess(["docker", "ps", "-a", "--filter", f"name={container}", "--format", "{{.Names}}"], stdout=subprocess.PIPE, text=True)
    containers = result.stdout.strip().split('\n') if result.stdout else []
    if container in containers:
        # If container exists but not running, start it
        running = get_running_containers()
        if container not in running:
            run_subprocess(["docker", "start", container], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        # Create and run
        run_subprocess(["docker", "run", "--name", container, "-dit", image], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def update_docker_compose_with_mount(container, image, mount_info):
    compose_data = {}
    if os.path.exists(DOCKER_COMPOSE_FILE):
        with open(DOCKER_COMPOSE_FILE, "r") as f:
            compose_data = yaml.safe_load(f) or {}

    if "services" not in compose_data:
        compose_data["services"] = {}

    if container not in compose_data["services"]:
        compose_data["services"][container] = {
            "image": image,
            "container_name": container,
            "volumes": []
        }

    service = compose_data["services"][container]
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
    with open(DOCKER_COMPOSE_FILE, "w") as f:
        yaml.dump(compose_data, f, default_flow_style=False)

def mount_dialog(root, container=None, image=None):
    """Show a dialog to add a mount to the container."""
    class MountDialog(simpledialog.Dialog):
        def body(self, master):
            containers = get_running_containers()
            Label(master, text="Select Container:").grid(row=0, column=0, sticky="w")
            self.container_var = StringVar(value=containers[0] if containers else (container or ""))
            self.container_menu = Combobox(master, textvariable=self.container_var, values=containers, state='readonly')
            self.container_menu.grid(row=0, column=1, sticky="ew")

            Label(master, text="Host Folder:").grid(row=1, column=0, sticky="w")
            self.host_folder_var = StringVar()
            self.host_folder_entry = Entry(master, textvariable=self.host_folder_var, width=40)
            self.host_folder_entry.grid(row=1, column=1, sticky="ew")
            self.browse_btn = Button(master, text="Browse...", command=self.browse_folder)
            self.browse_btn.grid(row=1, column=2, sticky="w")

            Label(master, text="Mount Point in Container:").grid(row=2, column=0, sticky="w")
            self.container_path_var = StringVar(value="/mnt/shared")
            self.container_path_entry = Entry(master, textvariable=self.container_path_var, width=40)
            self.container_path_entry.grid(row=2, column=1, sticky="ew")

            self.readonly_var = BooleanVar()
            self.readonly_check = Checkbutton(master, text="Read Only", variable=self.readonly_var)
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

    dlg = MountDialog(root)
    if hasattr(dlg, "result") and dlg.result:
        mount_info = dlg.result
        update_docker_compose_with_mount(mount_info["container"], image or "lispmachine", mount_info)
        # Restart the container with new mount
        run_subprocess(["docker", "stop", mount_info["container"]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        run_subprocess(["docker", "rm", mount_info["container"]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        vol_flag = f"{mount_info['host_folder']}:{mount_info['mount_point']}"
        if mount_info["readonly"]:
            vol_flag += ":ro"
        run_proc = run_subprocess(
            ["docker", "run", "--name", mount_info["container"], "-dit", "-v", vol_flag, image or "lispmachine"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if run_proc.returncode == 0:
            messagebox.showinfo("Success", f"Mounted {mount_info['host_folder']} to {mount_info['mount_point']} ({'read-only' if mount_info['readonly'] else 'rw'}) in {mount_info['container']}.")
        else:
            messagebox.showerror("Docker Error", run_proc.stderr)
