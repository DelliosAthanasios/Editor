import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import os
import tempfile
import shutil
import platform

class CPPBytecodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("C/C++ Code Editor with Assembly Viewer")
        self.root.geometry("1200x800")
        
        # Available compilers configuration
        self.compilers = {
            'gcc': {'name': 'GCC', 'c_flag': '-std=c11', 'cpp_flag': '-std=c++17'},
            'clang': {'name': 'Clang', 'c_flag': '-std=c11', 'cpp_flag': '-std=c++17'},
            'g++': {'name': 'G++', 'c_flag': '-std=c11', 'cpp_flag': '-std=c++17'},
            'clang++': {'name': 'Clang++', 'c_flag': '-std=c11', 'cpp_flag': '-std=c++17'},
        }
        
        # Check for available compilers
        self.available_compilers = self.scan_compilers()
        self.current_compiler = None
        self.current_language = 'c'  # 'c' or 'cpp'
        
        if not self.available_compilers:
            self.show_compiler_warning()
        else:
            self.current_compiler = list(self.available_compilers.keys())[0]
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create menu bar
        self.create_menu()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create paned window for splitting
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for C/C++ editor
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # Create right frame for assembly viewer
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # Setup C/C++ editor
        self.setup_code_editor()
        
        # Setup assembly viewer
        self.setup_assembly_viewer()
        
        # Setup auto-update
        self.setup_auto_update()
        
        # Default C code
        self.default_c_code = '''#include <stdio.h>

int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

int main() {
    int result = fibonacci(10);
    printf("Fibonacci(10) = %d\\n", result);
    return 0;
}
'''
        
        # Default C++ code
        self.default_cpp_code = '''#include <iostream>
#include <vector>
#include <algorithm>

class Calculator {
public:
    static int fibonacci(int n) {
        if (n <= 1) return n;
        return fibonacci(n - 1) + fibonacci(n - 2);
    }
    
    static std::vector<int> generateSequence(int count) {
        std::vector<int> sequence;
        for (int i = 0; i < count; ++i) {
            sequence.push_back(fibonacci(i));
        }
        return sequence;
    }
};

int main() {
    auto sequence = Calculator::generateSequence(10);
    
    std::cout << "Fibonacci sequence: ";
    for (int num : sequence) {
        std::cout << num << " ";
    }
    std::cout << std::endl;
    
    return 0;
}
'''
        
        # Load default code
        self.load_default_code()
        if self.available_compilers:
            self.update_assembly_from_code()
    
    def scan_compilers(self):
        """Scan system for available C/C++ compilers"""
        available = {}
        
        for compiler, info in self.compilers.items():
            if shutil.which(compiler):
                try:
                    # Get compiler version
                    result = subprocess.run([compiler, '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        version_line = result.stdout.split('\n')[0]
                        available[compiler] = {
                            'name': info['name'],
                            'version': version_line,
                            'c_flag': info['c_flag'],
                            'cpp_flag': info['cpp_flag']
                        }
                except Exception:
                    pass
        
        return available
    
    def show_compiler_warning(self):
        """Show warning about missing compilers"""
        warning = (
            "No C/C++ compilers found!\n\n"
            "This application requires at least one C/C++ compiler to be installed and available in your PATH.\n\n"
            "Supported compilers:\n"
            "• GCC (gcc/g++)\n"
            "• Clang (clang/clang++)\n\n"
            "Without a compiler, assembly generation will not work.\n\n"
            "Please install a compiler for your platform."
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
        edit_menu.add_command(label="Undo", command=lambda: self.code_text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", command=lambda: self.code_text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.code_text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.code_text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.code_text.event_generate("<<Paste>>"))
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Assembly", command=self.update_assembly_from_code)
        view_menu.add_command(label="Check Compilers", command=self.check_compiler_status)
        
        # Language menu
        language_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Language", menu=language_menu)
        language_menu.add_command(label="Switch to C", command=lambda: self.switch_language('c'))
        language_menu.add_command(label="Switch to C++", command=lambda: self.switch_language('cpp'))
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-S>', lambda e: self.save_as_file())
    
    def create_toolbar(self):
        """Create the toolbar with compiler selection"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Language selection
        ttk.Label(toolbar, text="Language:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.language_var = tk.StringVar(value='C')
        language_combo = ttk.Combobox(toolbar, textvariable=self.language_var,
                                    values=['C', 'C++'], state='readonly', width=8)
        language_combo.pack(side=tk.LEFT, padx=(0, 10))
        language_combo.bind('<<ComboboxSelected>>', self.on_language_change)
        
        # Compiler selection
        ttk.Label(toolbar, text="Compiler:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.compiler_var = tk.StringVar()
        self.compiler_combo = ttk.Combobox(toolbar, textvariable=self.compiler_var,
                                         state='readonly', width=20)
        self.compiler_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.compiler_combo.bind('<<ComboboxSelected>>', self.on_compiler_change)
        
        # Update compiler list
        self.update_compiler_list()
        
        # Optimization level
        ttk.Label(toolbar, text="Optimization:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.optimization_var = tk.StringVar(value='-O0')
        opt_combo = ttk.Combobox(toolbar, textvariable=self.optimization_var,
                               values=['-O0', '-O1', '-O2', '-O3', '-Os', '-Ofast'],
                               state='readonly', width=8)
        opt_combo.pack(side=tk.LEFT, padx=(0, 10))
        opt_combo.bind('<<ComboboxSelected>>', self.on_optimization_change)
        
        # Compile button
        self.compile_btn = ttk.Button(toolbar, text="Compile", command=self.update_assembly_from_code)
        self.compile_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        if not self.available_compilers:
            self.compile_btn.config(state='disabled')
    
    def update_compiler_list(self):
        """Update the compiler dropdown list"""
        if not self.available_compilers:
            self.compiler_combo['values'] = ['No compilers found']
            self.compiler_combo.set('No compilers found')
            return
        
        compiler_names = []
        for compiler, info in self.available_compilers.items():
            compiler_names.append(f"{info['name']} ({compiler})")
        
        self.compiler_combo['values'] = compiler_names
        
        if self.current_compiler:
            current_name = f"{self.available_compilers[self.current_compiler]['name']} ({self.current_compiler})"
            self.compiler_combo.set(current_name)
        elif compiler_names:
            self.compiler_combo.set(compiler_names[0])
            self.current_compiler = list(self.available_compilers.keys())[0]
    
    def on_language_change(self, event=None):
        """Handle language change"""
        if self.language_var.get() == 'C':
            self.current_language = 'c'
        else:
            self.current_language = 'cpp'
        
        self.update_title()
        if self.available_compilers:
            self.update_assembly_from_code()
    
    def on_compiler_change(self, event=None):
        """Handle compiler change"""
        selected = self.compiler_var.get()
        if selected and selected != 'No compilers found':
            # Extract compiler name from display string
            compiler_name = selected.split('(')[1].rstrip(')')
            self.current_compiler = compiler_name
            self.update_title()
            if self.available_compilers:
                self.update_assembly_from_code()
    
    def on_optimization_change(self, event=None):
        """Handle optimization level change"""
        if self.available_compilers:
            self.update_assembly_from_code()
    
    def switch_language(self, language):
        """Switch between C and C++"""
        if language == 'c':
            self.language_var.set('C')
            self.current_language = 'c'
        else:
            self.language_var.set('C++')
            self.current_language = 'cpp'
        
        # Ask if user wants to load default code
        if messagebox.askyesno("Switch Language", 
                             f"Load default {language.upper()} code? This will replace current code."):
            self.load_default_code()
        
        self.update_title()
        if self.available_compilers:
            self.update_assembly_from_code()
    
    def load_default_code(self):
        """Load default code for current language"""
        self.code_text.delete('1.0', tk.END)
        if self.current_language == 'c':
            self.code_text.insert(tk.END, self.default_c_code)
        else:
            self.code_text.insert(tk.END, self.default_cpp_code)
    
    def update_title(self):
        """Update window title with current language and compiler"""
        lang = self.current_language.upper()
        compiler = self.current_compiler if self.current_compiler else 'No compiler'
        self.root.title(f"{lang} Code Editor with Assembly Viewer - {compiler}")
    
    def check_compiler_status(self):
        """Check and display compiler status"""
        self.available_compilers = self.scan_compilers()
        
        if not self.available_compilers:
            message = "No C/C++ compilers found in your system PATH."
            message += "\n\nSupported compilers:"
            message += "\n• GCC (gcc/g++)"
            message += "\n• Clang (clang/clang++)"
            message += "\n\nAssembly generation will not work without a compiler."
            messagebox.showinfo("Compiler Status", message)
        else:
            message = f"Found {len(self.available_compilers)} compiler(s):\n\n"
            for compiler, info in self.available_compilers.items():
                message += f"• {info['name']} ({compiler})\n  {info['version']}\n\n"
            messagebox.showinfo("Compiler Status", message)
        
        self.update_compiler_list()
        self.update_assembly_display()
    
    def update_assembly_display(self):
        """Update assembly display based on compiler availability"""
        if self.available_compilers:
            self.update_assembly_from_code()
            self.compile_btn.config(state='normal')
            self.assembly_text.config(state='normal')
            compiler_name = self.available_compilers.get(self.current_compiler, {}).get('name', 'Unknown')
            self.assembly_title.config(text=f"Assembly Output ({compiler_name})")
        else:
            self.compile_btn.config(state='disabled')
            self.assembly_text.config(state='disabled')
            self.assembly_title.config(text="Assembly Output - NO COMPILER FOUND")
    
    def setup_code_editor(self):
        """Setup the C/C++ code editor"""
        self.editor_title = ttk.Label(self.left_frame, text="C/C++ Code Editor", 
                                    font=('Arial', 12, 'bold'))
        self.editor_title.pack(pady=(0, 5))
        
        line_frame = ttk.Frame(self.left_frame)
        line_frame.pack(fill=tk.BOTH, expand=True)
        
        self.line_numbers = tk.Text(line_frame, width=4, padx=3, takefocus=0,
                                  border=0, state='disabled', wrap='none',
                                  background='#f0f0f0', foreground='#666666')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        self.code_text = scrolledtext.ScrolledText(
            line_frame,
            wrap=tk.NONE,
            font=('Consolas', 11),
            undo=True,
            maxundo=50,
            tabs=('1c', '2c', '3c', '4c', '5c', '6c', '7c', '8c')
        )
        self.code_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.code_text.bind('<KeyRelease>', self.on_content_changed)
        self.code_text.bind('<Button-1>', self.on_content_changed)
        self.code_text.bind('<MouseWheel>', self.on_content_changed)
        
        self.status_bar = ttk.Label(self.left_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_assembly_viewer(self):
        """Setup the assembly viewer"""
        title_text = "Assembly Output"
        if self.available_compilers and self.current_compiler:
            compiler_name = self.available_compilers[self.current_compiler]['name']
            title_text = f"Assembly Output ({compiler_name})"
        elif not self.available_compilers:
            title_text = "Assembly Output - NO COMPILER FOUND"
        
        self.assembly_title = ttk.Label(self.right_frame, text=title_text, 
                                      font=('Arial', 12, 'bold'))
        self.assembly_title.pack(pady=(0, 5))
        
        self.assembly_text = scrolledtext.ScrolledText(
            self.right_frame,
            wrap=tk.NONE,
            font=('Consolas', 10),
            background='#f0f8ff',
            state='normal'
        )
        self.assembly_text.pack(fill=tk.BOTH, expand=True)
        
        if not self.available_compilers:
            self.assembly_text.insert(tk.END, 
                "No C/C++ compilers found!\n\n"
                "This application requires at least one C/C++ compiler to be installed and available in your PATH.\n\n"
                "Supported compilers:\n"
                "• GCC (gcc/g++)\n"
                "• Clang (clang/clang++)\n\n"
                "Without a compiler, assembly generation will not work.\n\n"
                "Please install a compiler for your platform."
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
                                    command=self.update_assembly_from_code,
                                    state='normal' if self.available_compilers else 'disabled')
        self.refresh_btn.pack(side=tk.LEFT)
    
    def setup_auto_update(self):
        """Setup auto-update for assembly"""
        self.update_timer = None
        if self.available_compilers:
            self.code_text.bind('<KeyRelease>', self.schedule_assembly_update)
            self.code_text.bind('<<Modified>>', self.schedule_assembly_update)
    
    def schedule_assembly_update(self, event=None):
        """Schedule assembly update from code changes"""
        if not self.available_compilers:
            return
            
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
        self.update_timer = self.root.after(1500, self.update_assembly_from_code)
    
    def update_line_numbers(self):
        """Update line numbers in the editor"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        
        line_count = int(self.code_text.index('end-1c').split('.')[0])
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert('1.0', line_numbers_string)
        self.line_numbers.config(state='disabled')
    
    def on_content_changed(self, event=None):
        """Handle content changes"""
        self.update_line_numbers()
        line_num = int(self.code_text.index('end-1c').split('.')[0])
        self.status_bar.config(text=f"Lines: {line_num - 1}")
    
    def get_file_extension(self):
        """Get appropriate file extension for current language"""
        return '.c' if self.current_language == 'c' else '.cpp'
    
    def get_compiler_flags(self):
        """Get compiler flags for current language and compiler"""
        if not self.current_compiler or self.current_compiler not in self.available_compilers:
            return []
        
        compiler_info = self.available_compilers[self.current_compiler]
        std_flag = compiler_info['c_flag'] if self.current_language == 'c' else compiler_info['cpp_flag']
        
        optimization = self.optimization_var.get()
        
        return ['-S', std_flag, optimization, '-fverbose-asm']
    
    def update_assembly_from_code(self):
        """Update the assembly display from C/C++ code"""
        if not self.available_compilers or not self.current_compiler:
            return
            
        try:
            code = self.code_text.get('1.0', tk.END)
            
            if not code.strip():
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, "No code to compile")
                self.assembly_info.config(text="No code")
                return
            
            # Create temporary directory for all files
            temp_dir = tempfile.mkdtemp()
            extension = self.get_file_extension()
            temp_source_path = os.path.join(temp_dir, f"temp{extension}")
            temp_asm_path = os.path.join(temp_dir, "temp.s")
            
            # Write source code to file
            with open(temp_source_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Prepare compiler command
            compiler_flags = self.get_compiler_flags()
            cmd = [self.current_compiler] + compiler_flags + [temp_source_path, '-o', temp_asm_path]
            
            # Compile to generate assembly
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
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
                error_msg = result.stderr if result.stderr else "Compilation failed"
                self.assembly_text.insert(tk.END, error_msg)
                self.assembly_info.config(text="Compilation failed")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            # Read the assembly file
            if os.path.exists(temp_asm_path):
                try:
                    with open(temp_asm_path, 'r', encoding='utf-8') as asm_file:
                        assembly_output = asm_file.read()
                except UnicodeDecodeError:
                    with open(temp_asm_path, 'r', encoding='latin-1') as asm_file:
                        assembly_output = asm_file.read()
                
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, assembly_output)
                
                # Count non-empty, non-comment lines
                asm_lines = [line for line in assembly_output.split('\n') 
                           if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('.')]
                
                compiler_name = self.available_compilers[self.current_compiler]['name']
                optimization = self.optimization_var.get()
                self.assembly_info.config(text=f"Assembly lines: {len(asm_lines)} | {compiler_name} | {optimization}")
                
            else:
                self.assembly_text.delete('1.0', tk.END)
                self.assembly_text.insert(tk.END, "Assembly file not generated")
                self.assembly_info.config(text="No assembly output")
                
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
            self.code_text.delete('1.0', tk.END)
            if self.available_compilers:
                self.update_assembly_from_code()
    
    def open_file(self):
        """Open a C/C++ file"""
        filetypes = [
            ("C files", "*.c"),
            ("C++ files", "*.cpp;*.cxx;*.cc"),
            ("Header files", "*.h;*.hpp"),
            ("All files", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Open C/C++ File",
            filetypes=filetypes
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.code_text.delete('1.0', tk.END)
                    self.code_text.insert('1.0', content)
                    
                    # Auto-detect language from file extension
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.cpp', '.cxx', '.cc']:
                        self.current_language = 'cpp'
                        self.language_var.set('C++')
                    elif ext in ['.c']:
                        self.current_language = 'c'
                        self.language_var.set('C')
                    
                    self.update_title()
                    if self.available_compilers:
                        self.update_assembly_from_code()
                    self.status_bar.config(text=f"Opened: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        extension = self.get_file_extension()
        default_ext = extension
        
        if self.current_language == 'c':
            filetypes = [("C files", "*.c"), ("All files", "*.*")]
        else:
            filetypes = [("C++ files", "*.cpp"), ("C++ files", "*.cxx"), ("All files", "*.*")]
        
        file_path = filedialog.asksaveasfilename(
            title="Save C/C++ File",
            defaultextension=default_ext,
            filetypes=filetypes
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    content = self.code_text.get('1.0', tk.END)
                    file.write(content)
                    self.status_bar.config(text=f"Saved: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def save_as_file(self):
        """Save as a new file"""
        self.save_file()

def main():
    root = tk.Tk()
    app = CPPBytecodeEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()