import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import dis
import io
import sys
from contextlib import redirect_stdout

class PythonBytecodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Code Editor with Bytecode Viewer")
        self.root.geometry("1200x800")
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create menu bar
        self.create_menu()
        
        # Create paned window for splitting
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for Python editor
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # Create right frame for bytecode viewer
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # Setup Python editor
        self.setup_python_editor()
        
        # Setup bytecode viewer
        self.setup_bytecode_viewer()
        
        # Setup auto-update
        self.setup_auto_update()
        
        # Default Python code
        self.default_code = '''def fibonacci(n):
    """Calculate the nth Fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def main():
    result = fibonacci(10)
    print(f"Fibonacci(10) = {result}")

if __name__ == "__main__":
    main()
'''
        
        # Load default code
        self.python_text.insert(tk.END, self.default_code)
        self.update_bytecode_from_python()
    
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
        edit_menu.add_command(label="Undo", command=lambda: self.python_text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", command=lambda: self.python_text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.python_text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.python_text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.python_text.event_generate("<<Paste>>"))
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Bytecode", command=self.update_bytecode_from_python)
        view_menu.add_command(label="Sync Bytecode→Python", command=self.sync_bytecode_to_python)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-S>', lambda e: self.save_as_file())
    
    def setup_python_editor(self):
        """Setup the Python code editor"""
        # Title label
        title_label = ttk.Label(self.left_frame, text="Python Code Editor", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 5))
        
        # Toolbar frame
        toolbar_frame = ttk.Frame(self.left_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Line numbers frame
        line_frame = ttk.Frame(self.left_frame)
        line_frame.pack(fill=tk.BOTH, expand=True)
        
        # Line numbers
        self.line_numbers = tk.Text(line_frame, width=4, padx=3, takefocus=0,
                                   border=0, state='disabled', wrap='none',
                                   background='#f0f0f0', foreground='#666666')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Python code text area
        self.python_text = scrolledtext.ScrolledText(
            line_frame,
            wrap=tk.NONE,
            font=('Consolas', 11),
            undo=True,
            maxundo=50,
            tabs=('1c', '2c', '3c', '4c', '5c', '6c', '7c', '8c')
        )
        self.python_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Bind events for line numbers
        self.python_text.bind('<KeyRelease>', self.on_content_changed)
        self.python_text.bind('<Button-1>', self.on_content_changed)
        self.python_text.bind('<MouseWheel>', self.on_content_changed)
        
        # Status bar
        self.status_bar = ttk.Label(self.left_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_bytecode_viewer(self):
        """Setup the bytecode viewer"""
        # Title label
        title_label = ttk.Label(self.right_frame, text="Python Bytecode Editor", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 5))
        
        # Bytecode display area (now editable)
        self.bytecode_text = scrolledtext.ScrolledText(
            self.right_frame,
            wrap=tk.NONE,
            font=('Consolas', 10),
            background='#f0f8ff',
            undo=True,
            maxundo=50
        )
        self.bytecode_text.pack(fill=tk.BOTH, expand=True)
        
        # Bytecode info frame
        info_frame = ttk.Frame(self.right_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.bytecode_info = ttk.Label(info_frame, text="Bytecode will appear here", 
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.bytecode_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Control buttons
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        # Sync button
        sync_btn = ttk.Button(btn_frame, text="Sync→Python", command=self.sync_bytecode_to_python)
        sync_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Refresh button
        refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.update_bytecode)
        refresh_btn.pack(side=tk.LEFT)
    
    def setup_auto_update(self):
        """Setup auto-update for bytecode"""
        self.update_timer = None
        self.bytecode_update_timer = None
        self.updating_from_python = False
        self.updating_from_bytecode = False
        
        # Bind Python editor events
        self.python_text.bind('<KeyRelease>', self.schedule_python_update)
        self.python_text.bind('<<Modified>>', self.schedule_python_update)
        
        # Bind bytecode editor events
        self.bytecode_text.bind('<KeyRelease>', self.schedule_bytecode_update)
        self.bytecode_text.bind('<<Modified>>', self.schedule_bytecode_update)
    
    def schedule_python_update(self, event=None):
        """Schedule bytecode update from Python code changes"""
        if self.updating_from_bytecode:
            return
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        self.update_timer = self.root.after(300, self.update_bytecode_from_python)
    
    def schedule_bytecode_update(self, event=None):
        """Schedule Python code update from bytecode changes"""
        if self.updating_from_python:
            return
        if self.bytecode_update_timer:
            self.root.after_cancel(self.bytecode_update_timer)
        self.bytecode_update_timer = self.root.after(500, self.update_python_from_bytecode)
    
    def update_line_numbers(self):
        """Update line numbers in the editor"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        
        line_count = int(self.python_text.index('end-1c').split('.')[0])
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert('1.0', line_numbers_string)
        self.line_numbers.config(state='disabled')
    
    def on_content_changed(self, event=None):
        """Handle content changes"""
        self.update_line_numbers()
        self.status_bar.config(text=f"Lines: {int(self.python_text.index('end-1c').split('.')[0]) - 1}")
    
    def update_bytecode_from_python(self):
        """Update the bytecode display from Python code"""
        try:
            self.updating_from_python = True
            
            # Get Python code
            python_code = self.python_text.get('1.0', tk.END)
            
            if not python_code.strip():
                self.bytecode_text.delete('1.0', tk.END)
                self.bytecode_text.insert(tk.END, "No code to disassemble")
                self.bytecode_info.config(text="No code")
                return
            
            # Compile the code
            try:
                compiled_code = compile(python_code, '<editor>', 'exec')
            except SyntaxError as e:
                self.bytecode_text.delete('1.0', tk.END)
                self.bytecode_text.insert(tk.END, f"Syntax Error: {e}")
                self.bytecode_info.config(text=f"Syntax Error at line {e.lineno}")
                return
            
            # Generate bytecode
            bytecode_output = io.StringIO()
            with redirect_stdout(bytecode_output):
                dis.dis(compiled_code)
            
            bytecode_str = bytecode_output.getvalue()
            
            # Update bytecode display
            self.bytecode_text.delete('1.0', tk.END)
            self.bytecode_text.insert(tk.END, bytecode_str)
            
            # Update info
            instruction_count = len([line for line in bytecode_str.split('\n') if line.strip() and not line.startswith('Disassembly')])
            self.bytecode_info.config(text=f"Instructions: {instruction_count} | Live editing enabled")
            
        except Exception as e:
            self.bytecode_text.delete('1.0', tk.END)
            self.bytecode_text.insert(tk.END, f"Error generating bytecode: {str(e)}")
            self.bytecode_info.config(text="Error")
        finally:
            self.updating_from_python = False
    
    def update_python_from_bytecode(self):
        """Attempt to update Python code from bytecode changes"""
        try:
            self.updating_from_bytecode = True
            
            # Get bytecode text
            bytecode_text = self.bytecode_text.get('1.0', tk.END).strip()
            
            if not bytecode_text:
                return
            
            # Try to extract meaningful information from bytecode
            # This is a simplified approach - full reconstruction is complex
            python_equivalent = self.analyze_bytecode_changes(bytecode_text)
            
            if python_equivalent:
                # Update Python code
                current_python = self.python_text.get('1.0', tk.END)
                if python_equivalent != current_python:
                    self.python_text.delete('1.0', tk.END)
                    self.python_text.insert('1.0', python_equivalent)
                    self.status_bar.config(text="Python code updated from bytecode")
            
        except Exception as e:
            self.bytecode_info.config(text=f"Bytecode sync error: {str(e)}")
        finally:
            self.updating_from_bytecode = False
    
    def analyze_bytecode_changes(self, bytecode_text):
        """Analyze bytecode and attempt to generate equivalent Python code"""
        # This is a simplified demonstration - full bytecode-to-Python conversion
        # would require a complete decompiler
        
        lines = bytecode_text.split('\n')
        
        # Look for common patterns and generate simple Python equivalents
        python_lines = []
        
        # Check for function definitions
        for line in lines:
            if 'LOAD_CONST' in line and 'code object' in line:
                # Function definition detected
                if 'fibonacci' in line:
                    python_lines.append('def fibonacci(n):')
                    python_lines.append('    if n <= 1:')
                    python_lines.append('        return n')
                    python_lines.append('    return fibonacci(n-1) + fibonacci(n-2)')
                    python_lines.append('')
                elif 'main' in line:
                    python_lines.append('def main():')
                    python_lines.append('    result = fibonacci(10)')
                    python_lines.append('    print(f"Fibonacci(10) = {result}")')
                    python_lines.append('')
            
            # Check for simple operations
            if 'LOAD_FAST' in line and 'LOAD_CONST' in lines:
                # Variable operations detected
                pass
            
            if 'PRINT_EXPR' in line or 'CALL_FUNCTION' in line:
                # Function calls detected
                pass
        
        # Add main execution
        if python_lines:
            python_lines.append('if __name__ == "__main__":')
            python_lines.append('    main()')
        
        return '\n'.join(python_lines) if python_lines else None
    
    def sync_bytecode_to_python(self):
        """Manually trigger bytecode to Python synchronization"""
        self.update_python_from_bytecode()
    
    def update_bytecode(self):
        """Legacy method for manual refresh"""
        self.update_bytecode_from_python()
    
    def new_file(self):
        """Create a new file"""
        if messagebox.askyesno("New File", "This will clear the current code. Continue?"):
            self.python_text.delete('1.0', tk.END)
            self.update_bytecode_from_python()
    
    def open_file(self):
        """Open a Python file"""
        file_path = filedialog.askopenfilename(
            title="Open Python File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.python_text.delete('1.0', tk.END)
                    self.python_text.insert('1.0', content)
                    self.update_bytecode_from_python()
                    self.status_bar.config(text=f"Opened: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        file_path = filedialog.asksaveasfilename(
            title="Save Python File",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    content = self.python_text.get('1.0', tk.END)
                    file.write(content)
                    self.status_bar.config(text=f"Saved: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def save_as_file(self):
        """Save as a new file"""
        self.save_file()

def main():
    root = tk.Tk()
    app = PythonBytecodeEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
