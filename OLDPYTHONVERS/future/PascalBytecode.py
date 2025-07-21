import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import os
import tempfile
import shutil

class PascalBytecodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Pascal Code Editor with Assembly Viewer")
        self.root.geometry("1200x800")
        
        # Check for Pascal compiler
        self.compiler_available = self.check_pascal_compiler()
        if not self.compiler_available:
            self.show_compiler_warning()
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create menu bar
        self.create_menu()
        
        # Create paned window for splitting
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for Pascal editor
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # Create right frame for assembly viewer
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # Setup Pascal editor
        self.setup_pascal_editor()
        
        # Setup assembly viewer
        self.setup_assembly_viewer()
        
        # Setup auto-update
        self.setup_auto_update()
        
        # Default Pascal code
        self.default_code = '''program Fibonacci;

function Fibonacci(n: Integer): Integer;
begin
    if n <= 1 then
        Fibonacci := n
    else
        Fibonacci := Fibonacci(n - 1) + Fibonacci(n - 2);
end;

var
    result: Integer;
begin
    result := Fibonacci(10);
    WriteLn('Fibonacci(10) = ', result);
end.
'''
        
        # Load default code
        self.pascal_text.insert(tk.END, self.default_code)
        if self.compiler_available:
            self.update_assembly_from_pascal()
    
    def check_pascal_compiler(self):
        """Check if Pascal compiler is available in the system"""
        try:
            return shutil.which('fpc') is not None
        except Exception:
            return False
    
    def show_compiler_warning(self):
        """Show warning about missing Pascal compiler"""
        warning = (
            "Pascal compiler (FPC) not found!\n\n"
            "This application requires Free Pascal Compiler (fpc) to be installed and available in your PATH.\n\n"
            "Without it, assembly generation will not work.\n\n"
            "Please install FPC from:\n"
            "https://www.freepascal.org/"
        )
        messagebox.showwarning("Compiler Missing", warning)
    
    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=lambda: self.pascal_text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", command=lambda: self.pascal_text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.pascal_text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.pascal_text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.pascal_text.event_generate("<<Paste>>"))
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Assembly", command=self.update_assembly_from_pascal)
        view_menu.add_command(label="Check Compiler", command=self.check_compiler_status)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-S>', lambda e: self.save_as_file())
    
    def check_compiler_status(self):
        """Check and display compiler status"""
        self.compiler_available = self.check_pascal_compiler()
        status = "available" if self.compiler_available else "not available"
        message = f"Pascal compiler (FPC) is {status} in your system PATH."
        
        if not self.compiler_available:
            message += "\n\nAssembly generation will not work without it."
            message += "\nPlease install FPC from:\nhttps://www.freepascal.org/"
        
        messagebox.showinfo("Compiler Status", message)
        
        if self.compiler_available:
            self.update_assembly_from_pascal()
            self.refresh_btn.config(state='normal')
            self.assembly_text.config(state='normal')
            self.title_label.config(text="Assembly Output (FPC 3.2.2)")
        else:
            self.refresh_btn.config(state='disabled')
            self.assembly_text.config(state='disabled')
            self.title_label.config(text="Assembly Output (FPC 3.2.2) - COMPILER NOT FOUND")
    
    def setup_pascal_editor(self):
        """Setup the Pascal code editor"""
        title_label = ttk.Label(self.left_frame, text="Pascal Code Editor", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 5))
        
        toolbar_frame = ttk.Frame(self.left_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))
        
        line_frame = ttk.Frame(self.left_frame)
        line_frame.pack(fill=tk.BOTH, expand=True)
        
        self.line_numbers = tk.Text(line_frame, width=4, padx=3, takefocus=0,
                                  border=0, state='disabled', wrap='none',
                                  background='#f0f0f0', foreground='#666666')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        self.pascal_text = scrolledtext.ScrolledText(
            line_frame,
            wrap=tk.NONE,
            font=('Consolas', 11),
            undo=True,
            maxundo=50,
            tabs=('1c', '2c', '3c', '4c', '5c', '6c', '7c', '8c')
        )
        self.pascal_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.pascal_text.bind('<KeyRelease>', self.on_content_changed)
        self.pascal_text.bind('<Button-1>', self.on_content_changed)
        self.pascal_text.bind('<MouseWheel>', self.on_content_changed)
        
        self.status_bar = ttk.Label(self.left_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_assembly_viewer(self):
        """Setup the assembly viewer"""
        title_text = "Assembly Output (FPC 3.2.2)"
        if not self.compiler_available:
            title_text += " - COMPILER NOT FOUND"
        self.title_label = ttk.Label(self.right_frame, text=title_text, font=('Arial', 12, 'bold'))
        self.title_label.pack(pady=(0, 5))
        
        self.assembly_text = scrolledtext.ScrolledText(
            self.right_frame,
            wrap=tk.NONE,
            font=('Consolas', 10),
            background='#f0f8ff',
            state='normal'
        )
        self.assembly_text.pack(fill=tk.BOTH, expand=True)
        
        if not self.compiler_available:
            self.assembly_text.insert(tk.END, 
                "Pascal compiler (FPC) not found!\n\n"
                "This application requires Free Pascal Compiler (fpc) to be installed and available in your PATH.\n\n"
                "Without it, assembly generation will not work.\n\n"
                "Please install FPC from:\n"
                "https://www.freepascal.org/"
            )
            self.assembly_text.config(state='disabled')
        
        info_frame = ttk.Frame(self.right_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.assembly_info = ttk.Label(info_frame, text="Assembly will appear here", 
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.assembly_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh", 
                                    command=self.update_assembly_from_pascal,
                                    state='normal' if self.compiler_available else 'disabled')
        self.refresh_btn.pack(side=tk.LEFT)
    
    def setup_auto_update(self):
        """Setup auto-update for assembly"""
        self.update_timer = None
        if self.compiler_available:
            self.pascal_text.bind('<KeyRelease>', self.schedule_assembly_update)
            self.pascal_text.bind('<<Modified>>', self.schedule_assembly_update)
    
    def schedule_assembly_update(self, event=None):
        """Schedule assembly update from Pascal code changes"""
        if not self.compiler_available:
            return
            
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        self.update_timer = self.root.after(1000, self.update_assembly_from_pascal)
    
    def update_line_numbers(self):
        """Update line numbers in the editor"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        
        line_count = int(self.pascal_text.index('end-1c').split('.')[0])
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert('1.0', line_numbers_string)
        self.line_numbers.config(state='disabled')
    
    def on_content_changed(self, event=None):
        """Handle content changes"""
        self.update_line_numbers()
        # Fixed the TypeError by converting to int before subtraction
        line_num = int(self.pascal_text.index('end-1c').split('.')[0])
        self.status_bar.config(text=f"Lines: {line_num - 1}")
    
    def update_assembly_from_pascal(self):
        """Update the assembly display from Pascal code"""
        if not self.compiler_available:
            return
            
        try:
            pascal_code = self.pascal_text.get('1.0', tk.END)
            
            if not pascal_code.strip():
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, "No code to compile")
                self.assembly_info.config(text="No code")
                return
            
            # Create temporary directory for all files
            temp_dir = tempfile.mkdtemp()
            temp_pas_path = os.path.join(temp_dir, "temp.pas")
            temp_asm_path = os.path.join(temp_dir, "temp.s")
            temp_exe_path = os.path.join(temp_dir, "temp")
            
            # Write Pascal code to file
            with open(temp_pas_path, 'w', encoding='utf-8') as f:
                f.write(pascal_code)
            
            # Compile with FPC to generate assembly
            try:
                result = subprocess.run(
                    ['fpc', '-al', '-O-', '-Xs', temp_pas_path, '-o' + temp_exe_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )
            except subprocess.TimeoutExpired:
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, "Compilation timed out")
                self.assembly_info.config(text="Compilation timed out")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            if result.returncode != 0:
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, result.stderr or "Compilation failed")
                self.assembly_info.config(text="Compilation failed")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            # Look for the assembly file (it might have a different name)
            asm_files = [f for f in os.listdir(temp_dir) if f.endswith('.s')]
            
            if not asm_files:
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, "Assembly file not generated")
                self.assembly_info.config(text="No assembly output")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            # Read the first .s file found
            asm_file_path = os.path.join(temp_dir, asm_files[0])
            
            try:
                # Try UTF-8 first, fall back to latin-1 if that fails
                try:
                    with open(asm_file_path, 'r', encoding='utf-8') as asm_file:
                        assembly_output = asm_file.read()
                except UnicodeDecodeError:
                    with open(asm_file_path, 'r', encoding='latin-1') as asm_file:
                        assembly_output = asm_file.read()
                
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, assembly_output)
                
                asm_lines = [line for line in assembly_output.split('\n') 
                            if line.strip() and not line.strip().startswith('#')]
                self.assembly_info.config(text=f"Assembly lines: {len(asm_lines)}")
                
            except Exception as e:
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, f"Error reading assembly file: {str(e)}")
                self.assembly_info.config(text="Read error")
                
        except Exception as e:
            self.assembly_text.delete('1.0', tk.END)
            self.assembly_text.insert(tk.END, f"Error generating assembly: {str(e)}")
            self.assembly_info.config(text="Error")
        finally:
            # Clean up temporary directory
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def new_file(self):
        """Create a new file"""
        if messagebox.askyesno("New File", "This will clear the current code. Continue?"):
            self.pascal_text.delete('1.0', tk.END)
            if self.compiler_available:
                self.update_assembly_from_pascal()
    
    def open_file(self):
        """Open a Pascal file"""
        file_path = filedialog.askopenfilename(
            title="Open Pascal File",
            filetypes=[("Pascal files", "*.pas"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.pascal_text.delete('1.0', tk.END)
                    self.pascal_text.insert('1.0', content)
                    if self.compiler_available:
                        self.update_assembly_from_pascal()
                    self.status_bar.config(text=f"Opened: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        file_path = filedialog.asksaveasfilename(
            title="Save Pascal File",
            defaultextension=".pas",
            filetypes=[("Pascal files", "*.pas"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    content = self.pascal_text.get('1.0', tk.END)
                    file.write(content)
                    self.status_bar.config(text=f"Saved: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def save_as_file(self):
        """Save as a new file"""
        self.save_file()

def main():
    root = tk.Tk()
    app = PascalBytecodeEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()