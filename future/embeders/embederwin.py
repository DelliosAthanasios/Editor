import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import win32gui
import win32con
import win32process
import win32api
import threading
import time
import os
import subprocess
from collections import namedtuple
from pathlib import Path

# Structure to hold window information
WindowInfo = namedtuple('WindowInfo', ['hwnd', 'title', 'process_name', 'visible'])

class MinimalWindowEmbedder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NeoEmbed")
        self.root.geometry("1200x700")
        self.root.minsize(800, 500)
        
        # Terminal color scheme
        self.bg = '#1a1a1a'      # Dark background
        self.fg = '#c5c8c6'      # Light text
        self.accent = '#81a2be'   # Blue accent
        self.green = '#b5bd68'    # Green
        self.red = '#cc6666'      # Red
        self.yellow = '#f0c674'   # Yellow
        self.select = '#373b41'   # Selection
        
        self.root.configure(bg=self.bg)
        
        # Store embedded windows info
        self.embedded_windows = {}
        self.embed_containers = []
        self.panel_visible = True  # Track panel visibility
        self.menu_visible = True   # Track menu visibility
        
        self.setup_ui()
        self.refresh_windows()
        self.start_auto_refresh()  # Start automatic refresh
        
    def start_auto_refresh(self):
        """Start automatic refresh of window list"""
        self.auto_refresh_id = self.root.after(5000, self.auto_refresh)
        
    def auto_refresh(self):
        """Automatic refresh function"""
        self.refresh_windows()
        # Schedule next refresh
        self.auto_refresh_id = self.root.after(5000, self.auto_refresh)
        
    def setup_ui(self):
        """Set up minimal terminal-style UI"""
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Treeview style
        style.configure('Terminal.Treeview',
                       background=self.bg,
                       foreground=self.fg,
                       fieldbackground=self.bg,
                       borderwidth=0,
                       relief='flat')
        style.map('Terminal.Treeview',
                 background=[('selected', self.select)],
                 foreground=[('selected', self.fg)])
        
        # Main frame
        self.main = tk.Frame(self.root, bg=self.bg)
        self.main.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Command bar
        self.cmd_frame = tk.Frame(self.main, bg=self.bg, height=25)
        self.cmd_frame.pack(fill=tk.X, pady=(0, 1))
        self.cmd_frame.pack_propagate(False)
        
        # Commands
        commands = [
            ("F1:Refresh", self.refresh_windows),
            ("F2:Embed", self.embed_window),
            ("F3:Release", self.release_selected_window),
            ("F5:Toggle Panel", self.toggle_panel),
            ("F6:Full Screen", self.toggle_menu),
        ]
        
        for i, (text, cmd) in enumerate(commands):
            btn = tk.Label(self.cmd_frame, text=text, bg=self.bg, fg=self.fg,
                          font=('Courier', 8), cursor='hand2',
                          relief='flat', padx=3)
            btn.pack(side=tk.LEFT, padx=1)
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            
            # Bind function keys
            fkey = text.split(':')[0]  # Get key from text
            if fkey:
                self.root.bind(f"<{fkey}>", lambda e, c=cmd: c())
        
        # Content area
        self.content = tk.Frame(self.main, bg=self.bg)
        self.content.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Window list
        self.left = tk.Frame(self.content, bg=self.bg, width=350)
        self.left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        self.left.pack_propagate(False)
        
        # Header
        tk.Label(self.left, text="Windows", bg=self.bg, fg=self.accent,
                font=('Courier', 10, 'bold')).pack(pady=2)
        
        # Window list
        self.tree = ttk.Treeview(self.left, columns=('proc', 'stat'), show='tree headings',
                                height=20, style='Terminal.Treeview')
        self.tree.heading('#0', text='Title', anchor='w')
        self.tree.heading('proc', text='Process', anchor='w')
        self.tree.heading('stat', text='Status', anchor='w')
        self.tree.column('#0', width=200, minwidth=150)
        self.tree.column('proc', width=80, minwidth=60)
        self.tree.column('stat', width=50, minwidth=40)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Status area
        status_frame = tk.Frame(self.left, bg=self.bg, height=100)
        status_frame.pack(fill=tk.X, pady=2)
        status_frame.pack_propagate(False)
        
        tk.Label(status_frame, text="Status", bg=self.bg, fg=self.accent,
                font=('Courier', 9, 'bold')).pack()
        
        self.status_text = tk.Text(status_frame, height=5, bg=self.bg, fg=self.fg,
                                  font=('Courier', 8), wrap=tk.WORD, relief='flat',
                                  borderwidth=0, insertbackground=self.fg)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=2)
        
        # Right panel - Embed area
        self.right_panel = tk.Frame(self.content, bg=self.bg)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self.on_window_select)
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Return>', lambda e: self.embed_window())
        
        # Keyboard shortcuts
        self.root.bind('<Control-r>', lambda e: self.refresh_windows())
        self.root.bind('<Control-e>', lambda e: self.embed_window())
        self.root.bind('<Control-d>', lambda e: self.release_selected_window())
        self.root.bind('<F11>', lambda e: self.toggle_panel())  # Additional shortcut
        
        # Create menu toggle button but hide initially
        self.menu_toggle_btn = tk.Button(self.main, text="☰", bg=self.bg, fg=self.fg,
                                        font=('Arial', 10), relief='flat', 
                                        command=self.toggle_menu)
        self.menu_toggle_btn.place(relx=1.0, x=-5, y=5, anchor='ne')
        self.menu_toggle_btn.place_forget()  # Hide initially
        
        self.setup_embed_area()
        
    def toggle_menu(self):
        """Toggle visibility of the menu bar"""
        if self.menu_visible:
            # Hide menu
            self.cmd_frame.pack_forget()
            self.menu_visible = False
            # Show toggle button
            self.menu_toggle_btn.place(relx=1.0, x=-5, y=5, anchor='ne')
            self.update_status("Menu hidden - Press F6 to show")
        else:
            # Show menu
            self.cmd_frame.pack(fill=tk.X, pady=(0, 1))
            self.menu_visible = True
            # Hide toggle button
            self.menu_toggle_btn.place_forget()
            self.update_status("Menu shown")
        
    def toggle_panel(self):
        """Toggle visibility of the left panel"""
        if self.panel_visible:
            # Hide the panel
            self.left.pack_forget()
            self.panel_visible = False
            self.update_status("Panel hidden - Press F5 to show")
        else:
            # Show the panel
            self.left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
            self.panel_visible = True
            self.update_status("Panel shown")
        
    def setup_embed_area(self):
        """Setup embed containers"""
        for widget in self.right_panel.winfo_children():
            widget.destroy()
        self.embed_containers.clear()
        
        # Create a single container that takes the full space
        container = self.create_container(self.right_panel)
        container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.embed_containers.append(container)
        
        self.update_status("Embed area ready")
        
    def create_container(self, parent):
        """Create minimal embed container"""
        container = tk.Frame(parent, bg=self.bg, relief='solid', bd=1, highlightcolor=self.accent)
        
        # Simple header
        header = tk.Frame(container, bg=self.select, height=20)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="[empty]", bg=self.select, fg=self.fg,
                              font=('Courier', 8), anchor='w')
        title_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Embed area
        embed_frame = tk.Frame(container, bg=self.bg)
        embed_frame.pack(fill=tk.BOTH, expand=True)
        
        # Placeholder
        placeholder = tk.Label(embed_frame, text="<empty slot>", bg=self.bg, fg=self.select,
                              font=('Courier', 10), justify=tk.CENTER)
        placeholder.pack(expand=True)
        
        container.title_label = title_label
        container.embed_frame = embed_frame
        container.placeholder = placeholder
        container.embedded_hwnd = None
        
        return container
        
    def get_process_name(self, hwnd):
        """Get process name"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
            process_name = win32process.GetModuleFileNameEx(handle, 0).split('\\')[-1]
            win32api.CloseHandle(handle)
            return process_name
        except:
            return "?"
    
    def enum_windows_callback(self, hwnd, windows_list):
        """Enumerate windows callback"""
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and len(title.strip()) > 0:
                process_name = self.get_process_name(hwnd)
                windows_list.append(WindowInfo(hwnd, title, process_name, True))
    
    def refresh_windows(self):
        """Refresh window list"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        windows_list = []
        win32gui.EnumWindows(self.enum_windows_callback, windows_list)
        windows_list.sort(key=lambda x: x.title.lower())
        
        for window in windows_list:
            if "NeoEmbed" not in window.title:
                status = "+" if window.hwnd in self.embedded_windows else "-"
                self.tree.insert('', tk.END, text=window.title, 
                                values=(window.process_name, status), 
                                tags=(window.hwnd,))
        
        self.update_status(f"Scanned {len(windows_list)} windows")
    
    def on_window_select(self, event):
        """Handle selection"""
        pass  # Simplified - no button state management needed
    
    def on_double_click(self, event):
        """Handle double-click"""
        self.embed_window()
    
    def find_available_container(self):
        """Find available container"""
        for container in self.embed_containers:
            if container.embedded_hwnd is None:
                return container
        return None
    
    def embed_window(self):
        """Embed selected window"""
        selection = self.tree.selection()
        if not selection:
            self.update_status("No window selected")
            return
        
        hwnd = int(self.tree.item(selection[0], 'tags')[0])
        
        if hwnd in self.embedded_windows:
            self.update_status("Already embedded")
            return
        
        container = self.find_available_container()
        if not container:
            self.update_status("No free slots")
            return
        
        try:
            window_title = win32gui.GetWindowText(hwnd)
            
            container.embed_frame.update()
            embed_hwnd = container.embed_frame.winfo_id()
            original_parent = win32gui.GetParent(hwnd)
            
            win32gui.SetParent(hwnd, embed_hwnd)
            
            width = container.embed_frame.winfo_width()
            height = container.embed_frame.winfo_height()
            
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, width, height, 
                                 win32con.SWP_SHOWWINDOW)
            
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style = style & ~win32con.WS_CAPTION & ~win32con.WS_THICKFRAME & ~win32con.WS_MINIMIZE & ~win32con.WS_MAXIMIZE & ~win32con.WS_SYSMENU
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            self.embedded_windows[hwnd] = {
                'container': container,
                'original_parent': original_parent,
                'title': window_title
            }
            
            container.embedded_hwnd = hwnd
            container.title_label.config(text=f"[{window_title[:20]}...]" if len(window_title) > 20 else f"[{window_title}]")
            container.placeholder.destroy()
            
            threading.Thread(target=self.monitor_window, args=(hwnd,), daemon=True).start()
            
            self.update_status(f"Embedded: {window_title}")
            self.refresh_windows()
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
    
    def monitor_window(self, hwnd):
        """Monitor embedded window"""
        while hwnd in self.embedded_windows:
            try:
                if not win32gui.IsWindow(hwnd):
                    self.root.after(0, lambda: self.release_window(hwnd))
                    break
                self.root.after(0, lambda: self.update_window_size(hwnd))
                time.sleep(0.1)
            except:
                break
    
    def update_window_size(self, hwnd):
        """Update embedded window size"""
        if hwnd in self.embedded_windows:
            try:
                container = self.embedded_windows[hwnd]['container']
                if container.embed_frame.winfo_exists():
                    width = container.embed_frame.winfo_width()
                    height = container.embed_frame.winfo_height()
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 
                                         0, 0, width, height, win32con.SWP_SHOWWINDOW)
            except:
                pass
    
    def release_window(self, hwnd):
        """Release embedded window"""
        if hwnd not in self.embedded_windows:
            return
        
        try:
            window_info = self.embedded_windows[hwnd]
            container = window_info['container']
            
            win32gui.SetParent(hwnd, window_info['original_parent'] or 0)
            
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style = style | win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_SYSMENU
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
            container.embedded_hwnd = None
            container.title_label.config(text="[empty]")
            
            placeholder = tk.Label(container.embed_frame, text="<empty slot>", 
                                  bg=self.bg, fg=self.select, font=('Courier', 10))
            placeholder.pack(expand=True)
            container.placeholder = placeholder
            
            self.update_status(f"Released: {window_info['title']}")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        
        del self.embedded_windows[hwnd]
        self.refresh_windows()
    
    def release_selected_window(self):
        """Release selected window"""
        selection = self.tree.selection()
        if not selection:
            self.update_status("No window selected")
            return
            
        hwnd = int(self.tree.item(selection[0], 'tags')[0])
        
        if hwnd in self.embedded_windows:
            self.release_window(hwnd)
        else:
            self.update_status("Selected window is not embedded")
    
    def update_status(self, message):
        """Update status"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"{timestamp}: {message}\n")
        self.status_text.see(tk.END)
        
        lines = self.status_text.get("1.0", tk.END).split('\n')
        if len(lines) > 50:
            self.status_text.delete("1.0", f"{len(lines)-50}.0")
    
    def on_closing(self):
        """Handle closing"""
        # Cancel automatic refresh
        self.root.after_cancel(self.auto_refresh_id)
        
        # Release all embedded windows
        for hwnd in list(self.embedded_windows.keys()):
            self.release_window(hwnd)
            
        self.root.destroy()
    
    def run(self):
        """Run application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.focus_force()
        self.update_status("NeoEmbed ready")
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        import win32gui, win32con, win32process, win32api
    except ImportError:
        print("Error: pywin32 required. Install with: pip install pywin32")
        return
    
    print("NeoEmbed - Minimal Window Embedder")
    print("F1: Refresh | F2: Embed | F3: Release | F5: Toggle Panel | F6: Full Screen | F11: Toggle Panel")
    print("Starting...")
    
    try:
        app = MinimalWindowEmbedder()
        app.run()
    except KeyboardInterrupt:
        print("Shutdown.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()