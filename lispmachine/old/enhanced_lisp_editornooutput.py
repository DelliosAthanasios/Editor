import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
from tkinter import ttk
import subprocess
import threading
import time
import os
import json
import queue

class LispREPLDocker:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Lisp Docker REPL")
        self.root.geometry("1200x800")
        
        # Container state
        self.container_running = False
        self.container_name = "lisp_repl_session"
        self.process_queue = queue.Queue()
        
        # Setup UI
        self.setup_ui()
        self.setup_menu()
        
        # Auto-check container status on startup
        self.root.after(100, self.check_container_status)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-Return>', lambda e: self.send_code_thread())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<F5>', lambda e: self.send_code_thread())

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Status indicator
        self.status_frame = ttk.Frame(toolbar)
        self.status_frame.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(self.status_frame, text="Container: Stopped", 
                                     foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Control buttons
        ttk.Button(toolbar, text="Start Container", 
                  command=self.start_container).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Stop Container", 
                  command=self.stop_container).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Run Code (F5)", 
                  command=self.send_code_thread).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear Output", 
                  command=self.clear_output).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # File operations
        ttk.Button(toolbar, text="New", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        
        # Main content area with splitter
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Code editor
        left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Lisp Code Editor", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # Code text area with line numbers
        editor_frame = ttk.Frame(left_frame)
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.text = scrolledtext.ScrolledText(editor_frame, 
                                            font=("Courier New", 11),
                                            wrap=tk.NONE,
                                            undo=True,
                                            tabs=("2c",))
        self.text.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Output and REPL
        right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(right_frame, weight=1)
        
        # Tabbed output area
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Output tab
        self.output_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.output_frame, text="Output")
        
        ttk.Label(self.output_frame, text="Code Execution Output", 
                 font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.output_box = scrolledtext.ScrolledText(self.output_frame, 
                                                   font=("Courier New", 10),
                                                   bg="black", fg="lime",
                                                   wrap=tk.WORD)
        self.output_box.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Interactive REPL tab
        self.repl_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.repl_frame, text="Interactive REPL")
        
        ttk.Label(self.repl_frame, text="Interactive Lisp REPL", 
                 font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.repl_output = scrolledtext.ScrolledText(self.repl_frame, 
                                                    font=("Courier New", 10),
                                                    bg="#1e1e1e", fg="white",
                                                    wrap=tk.WORD, height=20)
        self.repl_output.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # REPL input
        repl_input_frame = ttk.Frame(self.repl_frame)
        repl_input_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(repl_input_frame, text="REPL> ").pack(side=tk.LEFT)
        self.repl_input = ttk.Entry(repl_input_frame, font=("Courier New", 10))
        self.repl_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.repl_input.bind('<Return>', self.send_repl_command)
        
        ttk.Button(repl_input_frame, text="Send", 
                  command=self.send_repl_command).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # Current file tracking
        self.current_file = None
        self.update_title()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Run menu
        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Start Container", command=self.start_container)
        run_menu.add_command(label="Stop Container", command=self.stop_container)
        run_menu.add_separator()
        run_menu.add_command(label="Run Code", command=self.send_code_thread, accelerator="F5")
        run_menu.add_command(label="Run Selection", command=self.run_selection)
        run_menu.add_separator()
        run_menu.add_command(label="Clear Output", command=self.clear_output)
        menubar.add_cascade(label="Run", menu=run_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def update_title(self):
        filename = os.path.basename(self.current_file) if self.current_file else "Untitled"
        self.root.title(f"Enhanced Lisp Docker REPL - {filename}")

    def update_status(self, message):
        self.status_bar.config(text=message)
        self.root.after(5000, lambda: self.status_bar.config(text="Ready"))

    def check_container_status(self):
        """Check if container is running and update status"""
        try:
            result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", 
                                   self.container_name],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                  text=True, timeout=5)
            if result.stdout.strip() == "true":
                self.container_running = True
                self.status_label.config(text="Container: Running", foreground="green")
            else:
                self.container_running = False
                self.status_label.config(text="Container: Stopped", foreground="red")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.container_running = False
            self.status_label.config(text="Container: Not Found", foreground="orange")

    def start_container(self):
        """Start the Lisp REPL container with better error handling"""
        if self.container_running:
            messagebox.showinfo("Container Running", 
                              "The Lisp REPL container is already running.")
            return
        
        self.update_status("Starting container...")
        threading.Thread(target=self._start_container_thread, daemon=True).start()

    def _start_container_thread(self):
        try:
            # Remove existing container if it exists but is stopped
            subprocess.run(["docker", "rm", self.container_name], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Start new container
            cmd = ["docker", "run", "-dit", "--name", self.container_name, 
                   "lisp-repl", "sbcl"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            self.container_running = True
            self.root.after(0, lambda: self.status_label.config(
                text="Container: Running", foreground="green"))
            self.root.after(0, lambda: self.update_status("Container started successfully"))
            
        except subprocess.CalledProcessError as e:
            self.container_running = False
            error_msg = f"Failed to start container: {e.stderr if e.stderr else str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.update_status("Failed to start container"))

    def stop_container(self):
        """Stop and remove the container"""
        if not self.container_running:
            messagebox.showinfo("Container", "No container is currently running.")
            return
        
        self.update_status("Stopping container...")
        threading.Thread(target=self._stop_container_thread, daemon=True).start()

    def _stop_container_thread(self):
        try:
            subprocess.run(["docker", "stop", self.container_name], check=True)
            subprocess.run(["docker", "rm", self.container_name], check=True)
            
            self.container_running = False
            self.root.after(0, lambda: self.status_label.config(
                text="Container: Stopped", foreground="red"))
            self.root.after(0, lambda: self.update_status("Container stopped"))
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to stop container: {e}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))

    def send_code_thread(self):
        """Run code in a separate thread"""
        if not self.container_running:
            messagebox.showwarning("No Container", 
                                 "Please start the container before running code.")
            return
        
        threading.Thread(target=self.send_code, daemon=True).start()

    def send_code(self):
        """Send code to container and display output"""
        code = self.text.get("1.0", tk.END).strip()
        if not code:
            self.root.after(0, lambda: messagebox.showwarning("Empty Code", 
                                                             "Please write some Lisp code to send."))
            return

        self.root.after(0, lambda: self.update_status("Running code..."))
        self.root.after(0, lambda: self.output_box.delete("1.0", tk.END))
        self.root.after(0, lambda: self.output_box.insert(tk.END, 
                                                         f">>> Running code:\n{code}\n\n>>> Output:\n"))

        try:
            # Create a temporary file in the container and execute it
            temp_filename = f"/tmp/lisp_code_{int(time.time())}.lisp"
            
            # Write code to temporary file in container
            write_cmd = ["docker", "exec", "-i", self.container_name, 
                        "sh", "-c", f"cat > {temp_filename}"]
            write_process = subprocess.Popen(write_cmd,
                                           stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True)
            
            write_process.stdin.write(code)
            write_process.stdin.close()
            write_process.wait()
            
            # Execute the file
            exec_cmd = ["docker", "exec", self.container_name, 
                       "sbcl", "--script", temp_filename]
            process = subprocess.Popen(exec_cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True,
                                     bufsize=1)

            # Read output with timeout
            start_time = time.time()
            while process.poll() is None:
                if time.time() - start_time > 30:  # 30 second timeout
                    process.kill()
                    self.root.after(0, lambda: self.output_box.insert(tk.END, 
                                                                    "\n>>> Execution timed out (30s)\n"))
                    break
                
                line = process.stdout.readline()
                if line:
                    self.root.after(0, lambda l=line: self.output_box.insert(tk.END, l))
                    self.root.after(0, lambda: self.output_box.see(tk.END))

            # Read any remaining output
            remaining = process.stdout.read()
            if remaining:
                self.root.after(0, lambda: self.output_box.insert(tk.END, remaining))

            process.stdout.close()
            return_code = process.wait()
            
            # Clean up temporary file
            cleanup_cmd = ["docker", "exec", self.container_name, "rm", "-f", temp_filename]
            subprocess.run(cleanup_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.root.after(0, lambda: self.output_box.insert(tk.END, 
                                                            f"\n>>> Process completed (exit code: {return_code})\n"))
            self.root.after(0, lambda: self.update_status("Code execution completed"))

        except Exception as e:
            error_msg = f"Error executing code: {e}"
            self.root.after(0, lambda: self.output_box.insert(tk.END, f"\n>>> {error_msg}\n"))
            self.root.after(0, lambda: self.update_status("Code execution failed"))

    def run_selection(self):
        """Run only the selected text"""
        if not self.container_running:
            messagebox.showwarning("No Container", 
                                 "Please start the container before running code.")
            return
        
        try:
            selection = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if not selection.strip():
                messagebox.showwarning("No Selection", "Please select some code to run.")
                return
            
            # Temporarily replace text content with selection
            original_content = self.text.get("1.0", tk.END)
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", selection)
            
            # Run the selection
            self.send_code_thread()
            
            # Restore original content
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", original_content)
            
        except tk.TclError:
            messagebox.showwarning("No Selection", "Please select some code to run.")

    def send_repl_command(self, event=None):
        """Send command to interactive REPL"""
        if not self.container_running:
            messagebox.showwarning("No Container", 
                                 "Please start the container before using REPL.")
            return
        
        command = self.repl_input.get().strip()
        if not command:
            return
        
        self.repl_input.delete(0, tk.END)
        self.repl_output.insert(tk.END, f"REPL> {command}\n")
        self.repl_output.see(tk.END)
        
        threading.Thread(target=self._execute_repl_command, args=(command,), daemon=True).start()

    def _execute_repl_command(self, command):
        """Execute single REPL command"""
        try:
            # Create a temporary file for the command
            temp_filename = f"/tmp/repl_cmd_{int(time.time())}.lisp"
            
            # Write command to temporary file in container
            write_cmd = ["docker", "exec", "-i", self.container_name, 
                        "sh", "-c", f"cat > {temp_filename}"]
            write_process = subprocess.Popen(write_cmd,
                                           stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           text=True)
            
            write_process.stdin.write(command)
            write_process.stdin.close()
            write_process.wait()
            
            # Execute the command
            exec_cmd = ["docker", "exec", self.container_name, 
                       "sbcl", "--script", temp_filename]
            process = subprocess.Popen(exec_cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     text=True)
            
            output = process.stdout.read()
            process.wait()
            
            # Clean up temporary file
            cleanup_cmd = ["docker", "exec", self.container_name, "rm", "-f", temp_filename]
            subprocess.run(cleanup_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.root.after(0, lambda: self.repl_output.insert(tk.END, output + "\n"))
            self.root.after(0, lambda: self.repl_output.see(tk.END))
            
        except Exception as e:
            self.root.after(0, lambda: self.repl_output.insert(tk.END, f"Error: {e}\n"))

    def clear_output(self):
        """Clear the output window"""
        self.output_box.delete("1.0", tk.END)
        self.repl_output.delete("1.0", tk.END)

    def new_file(self):
        """Create a new file"""
        self.text.delete("1.0", tk.END)
        self.current_file = None
        self.update_title()

    def open_file(self):
        """Open a file"""
        filename = filedialog.askopenfilename(
            title="Open Lisp File",
            filetypes=[("Lisp files", "*.lisp *.lsp *.cl"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", content)
                self.current_file = filename
                self.update_title()
                self.update_status(f"Opened {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")

    def save_file(self):
        """Save the current file"""
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(self.text.get("1.0", tk.END))
                self.update_status(f"Saved {os.path.basename(self.current_file)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")
        else:
            self.save_as_file()

    def save_as_file(self):
        """Save the file with a new name"""
        filename = filedialog.asksaveasfilename(
            title="Save Lisp File",
            defaultextension=".lisp",
            filetypes=[("Lisp files", "*.lisp"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.text.get("1.0", tk.END))
                self.current_file = filename
                self.update_title()
                self.update_status(f"Saved as {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts = """Keyboard Shortcuts:

Ctrl+Return - Run code
F5 - Run code
Ctrl+S - Save file
Ctrl+O - Open file
Ctrl+N - New file

In REPL:
Enter - Send command
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)

    def show_about(self):
        """Show about dialog"""
        about_text = """Enhanced Lisp Docker REPL v2.0

A containerized Lisp development environment with:
• Interactive code editor
• Real-time code execution
• Interactive REPL
• File management
• Syntax highlighting support

Built with Python tkinter and Docker."""
        messagebox.showinfo("About", about_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = LispREPLDocker(root)
    root.mainloop()
