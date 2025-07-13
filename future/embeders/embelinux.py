import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import subprocess
from collections import namedtuple
from pathlib import Path
import re
#pip install pyxlib psutil
# Linux-specific imports
import Xlib
from Xlib import X, Xatom, display
from Xlib.error import XError
from Xlib.protocol import rq
import psutil

# Structure to hold window information
WindowInfo = namedtuple('WindowInfo', ['hwnd', 'title', 'process_name', 'visible'])

class LinuxWindowEmbedder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NeoEmbed Linux")
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
        
        # X11 setup
        self.disp = display.Display()
        self.root_win = self.disp.screen().root
        
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
        """Get process name for a window on Linux"""
        try:
            win = self.disp.create_resource_object('window', hwnd)
            pid = win.get_full_property(self.disp.intern_atom('_NET_WM_PID'), Xatom.CARDINAL).value[0]
            return psutil.Process(pid).name()
        except:
            return "?"
    
    def get_windows(self):
        """Get list of visible windows"""
        windows_list = []
        
        # Get list of client windows
        client_list = self.root_win.get_full_property(
            self.disp.intern_atom('_NET_CLIENT_LIST'), 
            Xatom.WINDOW
        )
        
        if client_list:
            for hwnd in client_list.value:
                try:
                    win = self.disp.create_resource_object('window', hwnd)
                    title = win.get_wm_name()
                    if not title:
                        title = win.get_full_property(
                            self.disp.intern_atom('_NET_WM_NAME'), 
                            self.disp.intern_atom('UTF8_STRING')
                        ).value.decode() if win.get_full_property(
                            self.disp.intern_atom('_NET_WM_NAME'), 
                            self.disp.intern_atom('UTF8_STRING')
                        ) else ""
                    
                    # Skip windows without titles
                    if not title:
                        continue
                    
                    # Skip our own windows
                    if "NeoEmbed" in title:
                        continue
                    
                    # Get window attributes to check visibility
                    attrs = win.get_attributes()
                    if attrs.map_state == X.IsViewable:
                        process_name = self.get_process_name(hwnd)
                        windows_list.append(WindowInfo(hwnd, title, process_name, True))
                except XError:
                    continue
        return windows_list
    
    def refresh_windows(self):
        """Refresh window list"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            windows_list = self.get_windows()
        except Exception as e:
            self.update_status(f"Error refreshing: {str(e)}")
            return
        
        windows_list.sort(key=lambda x: x.title.lower())
        
        for window in windows_list:
            status = "+" if window.hwnd in self.embedded_windows else "-"
            self.tree.insert('', tk.END, text=window.title, 
                            values=(window.process_name, status), 
                            tags=(window.hwnd,))
        
        self.update_status(f"Scanned {len(windows_list)} windows")
    
    def on_window_select(self, event):
        """Handle selection"""
        pass
    
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
            window_title = self.tree.item(selection[0])['text']
            
            container.embed_frame.update()
            embed_id = container.embed_frame.winfo_id()
            
            # Get Xlib objects
            embed_win = self.disp.create_resource_object('window', embed_id)
            target_win = self.disp.create_resource_object('window', hwnd)
            
            # Save original parent
            original_parent = target_win.query_tree().parent
            
            # Reparent the window
            target_win.reparent(embed_win, 0, 0)
            
            # Remove decorations
            motif_hints = [
                2,  # flags: indicate we are changing decorations
                0,  # functions: we don't change
                0,  # decorations: 0 means remove all
                0,  # input mode: leave as default
                0   # status: not used
            ]
            data = (32 * [0])
            for i, val in enumerate(motif_hints):
                data[i] = val
            atom = self.disp.intern_atom('_MOTIF_WM_HINTS')
            target_win.change_property(atom, atom, 32, data)
            
            # Resize the window
            width = container.embed_frame.winfo_width()
            height = container.embed_frame.winfo_height()
            target_win.configure(width=width, height=height)
            
            # Map the window (if it was unmapped)
            target_win.map()
            
            # Flush the display
            self.disp.flush()
            
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
                target_win = self.disp.create_resource_object('window', hwnd)
                # Check if window is still valid
                target_win.get_geometry()
                
                self.root.after(0, lambda: self.update_window_size(hwnd))
                time.sleep(0.1)
            except XError:
                # Window is gone
                self.root.after(0, lambda: self.release_window(hwnd))
                break
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
                    target_win = self.disp.create_resource_object('window', hwnd)
                    target_win.configure(width=width, height=height)
                    self.disp.flush()
            except:
                pass
    
    def release_window(self, hwnd):
        """Release embedded window"""
        if hwnd not in self.embedded_windows:
            return
        
        try:
            window_info = self.embedded_windows[hwnd]
            container = window_info['container']
            original_parent = window_info['original_parent']
            
            target_win = self.disp.create_resource_object('window', hwnd)
            
            # Reparent back to the original parent
            target_win.reparent(original_parent, 0, 0)
            
            # Reset motif hints (remove property)
            atom = self.disp.intern_atom('_MOTIF_WM_HINTS')
            target_win.delete_property(atom)
            
            # Map the window
            target_win.map()
            self.disp.flush()
            
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
        if hasattr(self, 'auto_refresh_id'):
            self.root.after_cancel(self.auto_refresh_id)
        
        # Release all embedded windows
        for hwnd in list(self.embedded_windows.keys()):
            self.release_window(hwnd)
            
        self.disp.close()
        self.root.destroy()
    
    def run(self):
        """Run application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.focus_force()
        self.update_status("NeoEmbed ready")
        self.root.mainloop()

def main():
    """Main entry point"""
    print("NeoEmbed - Minimal Window Embedder (Linux)")
    print("F1: Refresh | F2: Embed | F3: Release | F5: Toggle Panel | F6: Full Screen | F11: Toggle Panel")
    print("Starting...")
    
    try:
        app = LinuxWindowEmbedder()
        app.run()
    except KeyboardInterrupt:
        print("Shutdown.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
