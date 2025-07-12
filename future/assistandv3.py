import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import requests
import json
import threading
from typing import Optional
import os
import time
from datetime import datetime

class HuggingFaceCodeEditor:
    def __init__(self):
        self.api_token = None
        self.api_url = "https://api-inference.huggingface.co/models/"
        self.selected_model = "distilgpt2"  # Default model - changed to working model
        self.available_models = self.get_latest_models()  # Get latest models
        self.setup_ui()
        
    def fetch_working_models_from_hf(self):
        """Fetch working models directly from Hugging Face API"""
        working_models = []
        
        try:
            # Fetch models with text-generation pipeline
            response = requests.get(
                "https://huggingface.co/api/models?pipeline_tag=text-generation&sort=downloads&direction=-1&limit=50",
                timeout=15
            )
            
            if response.status_code == 200:
                models = response.json()
                
                # Test each model to see if it's actually available for inference
                for model in models[:20]:  # Test top 20 models
                    model_id = model['id']
                    try:
                        # Test if model is available for inference
                        test_url = f"{self.api_url}{model_id}"
                        test_headers = {"Content-Type": "application/json"}
                        if self.api_token:
                            test_headers["Authorization"] = f"Bearer {self.api_token}"
                        
                        test_data = {
                            "inputs": "Hello",
                            "parameters": {
                                "max_new_tokens": 10,
                                "temperature": 0.7
                            }
                        }
                        
                        test_response = requests.post(test_url, headers=test_headers, json=test_data, timeout=10)
                        
                        # If we get 200 (success) or 503 (loading), the model is available
                        if test_response.status_code in [200, 503]:
                            working_models.append(model_id)
                            print(f"✓ {model_id} - Available")
                        else:
                            print(f"✗ {model_id} - Not available (Status: {test_response.status_code})")
                            
                    except Exception as e:
                        print(f"✗ {model_id} - Error: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error fetching models from Hugging Face: {str(e)}")
            
        return working_models
        
    def get_latest_models(self):
        """Get the latest models from Hugging Face"""
        default_models = [
            "distilgpt2",
            "gpt2",
            "gpt2-medium",
            "gpt2-large",
            "gpt2-xl",
            "EleutherAI/gpt-neo-125M",
            "EleutherAI/gpt-neo-1.3B",
            "EleutherAI/gpt-neo-2.7B",
            "bigscience/bloom-560m",
            "facebook/opt-125m",
            "facebook/opt-350m",
            "facebook/opt-1.3b",
            "microsoft/DialoGPT-small",
            "microsoft/DialoGPT-medium",
            "microsoft/DialoGPT-large"
        ]
        
        try:
            # Try to fetch latest models from Hugging Face
            response = requests.get(
                "https://huggingface.co/api/models?pipeline_tag=text-generation&sort=downloads&direction=-1",
                timeout=10
            )
            if response.status_code == 200:
                models = response.json()
                # Get top 15 popular models
                popular_models = [model['id'] for model in models[:15]]
                # Combine and deduplicate
                all_models = list(set(default_models + popular_models))
                return sorted(all_models)[:25]  # Return top 25 models
        except Exception as e:
            print(f"Error fetching models: {str(e)}")
        
        # Fallback to default models if API call fails
        return default_models
        
    def refresh_models(self):
        """Refresh the list of available models"""
        self.available_models = self.get_latest_models()
        self.model_combo['values'] = self.available_models
        self.add_to_chat("System", f"Model list refreshed with {len(self.available_models)} available models")
        self.status_bar.config(text="Model list updated successfully")

    def scan_available_models(self):
        """Scan for actually working models from Hugging Face"""
        self.add_to_chat("System", "Scanning for working models from Hugging Face... This may take a few minutes.")
        self.status_bar.config(text="Scanning for working models...")
        
        # Run the scan in a separate thread
        def scan_thread():
            try:
                working_models = self.fetch_working_models_from_hf()
                
                if working_models:
                    # Update the model list
                    self.available_models = working_models
                    self.model_combo['values'] = working_models
                    
                    # Set the first working model as default
                    if working_models:
                        self.selected_model = working_models[0]
                        self.model_var.set(working_models[0])
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        f"Found {len(working_models)} working models:\n" + 
                        "\n".join([f"• {model}" for model in working_models[:10]]) + 
                        (f"\n... and {len(working_models)-10} more" if len(working_models) > 10 else "")))
                    self.root.after(0, lambda: self.status_bar.config(text=f"Found {len(working_models)} working models"))
                else:
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        "No working models found. Please check your internet connection or try again later."))
                    self.root.after(0, lambda: self.status_bar.config(text="No working models found"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.add_to_chat("System", f"Error scanning models: {str(e)}"))
                self.root.after(0, lambda: self.status_bar.config(text="Error scanning models"))
        
        threading.Thread(target=scan_thread, daemon=True).start()
        
    def setup_ui(self):
        """Initialize the main application UI"""
        self.root = tk.Tk()
        self.root.title("Hugging Face AI Code Editor")
        self.root.geometry("1200x800")
        
        # Check if API token exists
        if not self.load_api_token():
            self.show_api_token_dialog()
        else:
            self.create_main_interface()
            
    def load_api_token(self) -> bool:
        """Load API token from file if it exists"""
        try:
            if os.path.exists("hf_api_token.txt"):
                with open("hf_api_token.txt", "r") as f:
                    self.api_token = f.read().strip()
                return bool(self.api_token)
        except Exception:
            pass
        return False
        
    def save_api_token(self, api_token: str):
        """Save API token to file"""
        try:
            with open("hf_api_token.txt", "w") as f:
                f.write(api_token)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save API token: {str(e)}")
            
    def show_api_token_dialog(self):
        """Show API token input dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Hugging Face API Token Setup")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"600x400+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Hugging Face API Token Setup", 
                 font=("Arial", 16, "bold")).pack(pady=(0, 20))
        
        # Instructions
        instructions = tk.Text(frame, height=6, wrap=tk.WORD, font=("Arial", 9))
        instructions.pack(fill=tk.X, pady=(0, 10))
        instructions.insert(tk.END, 
            "To use this editor, you need a FREE Hugging Face API token:\n\n"
            "1. Go to https://huggingface.co/settings/tokens\n"
            "2. Create a new token (select 'Read' role)\n"
            "3. Copy the token and paste it below\n\n"
            "Note: Hugging Face API is completely FREE with rate limits that are generous for personal use.")
        instructions.config(state=tk.DISABLED)
        
        ttk.Label(frame, text="Enter your Hugging Face API token:").pack(pady=(10, 5))
        
        api_token_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=api_token_var, width=60, show="*")
        entry.pack(pady=(0, 10))
        entry.focus()
        
        # Option to skip token (some models work without it)
        skip_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Skip token setup (limited functionality)", 
                       variable=skip_var).pack(pady=(5, 10))
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=(10, 0))
        
        def save_and_continue():
            if skip_var.get():
                self.api_token = None
                dialog.destroy()
                self.create_main_interface()
                return
                
            api_token = api_token_var.get().strip()
            if not api_token:
                messagebox.showerror("Error", "Please enter a valid API token or check 'Skip token setup'")
                return
                
            self.api_token = api_token
            self.save_api_token(api_token)
            dialog.destroy()
            self.create_main_interface()
            
        def exit_app():
            self.root.quit()
            
        ttk.Button(button_frame, text="Save & Continue", 
                  command=save_and_continue).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Exit", 
                  command=exit_app).pack(side=tk.LEFT)
        
        # Bind Enter key to save
        entry.bind('<Return>', lambda e: save_and_continue())
        
    def create_main_interface(self):
        """Create the main editor interface"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # AI menu
        ai_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="AI Assistant", menu=ai_menu)
        ai_menu.add_command(label="Change API Token", command=self.change_api_token)
        ai_menu.add_command(label="Model Settings", command=self.show_model_settings)
        ai_menu.add_command(label="Scan for Working Models", command=self.scan_available_models)
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create paned window for resizable layout
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left frame for editor
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # Editor label and text area
        editor_header = ttk.Frame(left_frame)
        editor_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(editor_header, text="Code Editor", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        # Language selector
        ttk.Label(editor_header, text="Language:").pack(side=tk.RIGHT, padx=(10, 5))
        self.language_var = tk.StringVar(value="python")
        language_combo = ttk.Combobox(editor_header, textvariable=self.language_var, 
                                     values=["python", "javascript", "java", "cpp", "html", "css", "sql"],
                                     state="readonly", width=10)
        language_combo.pack(side=tk.RIGHT)
        
        # Text editor
        editor_frame = ttk.Frame(left_frame)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_editor = scrolledtext.ScrolledText(
            editor_frame, 
            wrap=tk.NONE, 
            font=("Consolas", 11),
            undo=True,
            maxundo=50,
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="#ffffff"
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True)
        
        # Right frame for AI chat
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # AI chat header
        chat_header = ttk.Frame(right_frame)
        chat_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(chat_header, text="AI Assistant", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        # Model selector with refresh button
        model_frame = ttk.Frame(chat_header)
        model_frame.pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.model_var = tk.StringVar(value=self.selected_model)
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.model_var, 
                                      values=self.available_models,
                                      state="readonly", width=25)
        self.model_combo.pack(side=tk.LEFT)
        self.model_combo.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # Add refresh button
        refresh_btn = ttk.Button(model_frame, text="🔄", width=2,
                                command=self.refresh_models)
        refresh_btn.pack(side=tk.LEFT, padx=(5, 0))
        ToolTip(refresh_btn, "Refresh model list from Hugging Face")
        
        # Add scan button
        scan_btn = ttk.Button(model_frame, text="🔍", width=2,
                             command=self.scan_available_models)
        scan_btn.pack(side=tk.LEFT, padx=(2, 0))
        ToolTip(scan_btn, "Scan for working models from Hugging Face")
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            right_frame, 
            wrap=tk.WORD, 
            font=("Arial", 10),
            height=20,
            state=tk.DISABLED,
            bg="#f8f9fa",
            fg="#333333"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Chat input frame
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Chat input
        self.chat_input = tk.Text(input_frame, height=3, font=("Arial", 10))
        self.chat_input.pack(fill=tk.X, pady=(0, 5))
        
        # Button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Send Message", 
                  command=self.send_message).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Analyze Code", 
                  command=self.analyze_code).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Generate Code", 
                  command=self.generate_code).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Test Connection", 
                  command=self.test_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Debug Connection", 
                  command=self.debug_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear Chat", 
                  command=self.clear_chat).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready - Using Hugging Face API", 
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.chat_input.bind('<Control-Return>', lambda e: self.send_message())
        
        # Initialize chat
        self.add_to_chat("Assistant", "Hello! I'm your free AI coding assistant powered by Hugging Face. I can help you write, review, and improve your code. Feel free to ask me anything!")
        
    def on_model_change(self, event=None):
        """Handle model selection change"""
        self.selected_model = self.model_var.get()
        self.add_to_chat("System", f"Switched to model: {self.selected_model}")
        
    def show_model_settings(self):
        """Show model settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Model Settings")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with refresh button
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Available Models", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(header_frame, text="Refresh Models", 
                                command=lambda: self.refresh_models_in_dialog(dialog))
        refresh_btn.pack(side=tk.RIGHT)
        
        # Scrollable container for models
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Model descriptions
        model_info = {
            "microsoft/DialoGPT-medium": "Good for conversations and general coding help",
            "microsoft/DialoGPT-large": "Better responses but slower",
            "bigscience/bloom-560m": "Multilingual model, good for various tasks",
            "EleutherAI/gpt-neo-1.3B": "General purpose text generation",
            "facebook/blenderbot-400M-distill": "Conversational AI, good for Q&A",
            "microsoft/CodeGPT-small-py": "Python code generation and completion",
            "huggingface/CodeBERTa-small-v1": "Code understanding and generation",
            "codellama/CodeLlama-7b-hf": "State-of-the-art code generation model",
            "mistralai/Mistral-7B-v0.1": "Efficient 7B parameter model",
            "google/gemma-7b": "Google's lightweight open model",
            "meta-llama/Llama-2-7b-chat-hf": "Meta's powerful conversational model",
            "tiiuae/falcon-7b-instruct": "High-performance instruction-following model",
            "stabilityai/stablelm-tuned-alpha-7b": "StableLM tuned for instruction following",
            "databricks/dolly-v2-7b": "Databricks' instruction-following model",
            "OpenAssistant/oasst-sft-4-pythia-12b-epoch-3.5": "OpenAssistant's large conversational model"
        }
        
        # Add models to the scrollable frame
        for model in self.available_models:
            frame_model = ttk.Frame(scrollable_frame)
            frame_model.pack(fill=tk.X, pady=2, padx=5)
            
            ttk.Radiobutton(frame_model, text=model, variable=self.model_var, 
                           value=model).pack(anchor=tk.W)
            
            # Get model description
            description = model_info.get(model, "Code/text generation model")
            last_updated = ""
            
            # Try to get model details
            try:
                model_data = requests.get(f"https://huggingface.co/api/models/{model}").json()
                if 'lastModified' in model_data:
                    last_modified = model_data['lastModified']
                    # Convert to readable date
                    if last_modified:
                        dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                        last_updated = f" • Updated: {dt.strftime('%Y-%m-%d')}"
            except Exception:
                pass
                
            ttk.Label(frame_model, 
                     text=f"{description}{last_updated}", 
                     font=("Arial", 8), 
                     foreground="gray").pack(anchor=tk.W, padx=(20, 0))
        
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(pady=(20, 0))
        
    def refresh_models_in_dialog(self, dialog):
        """Refresh models and update the dialog"""
        self.refresh_models()
        dialog.destroy()
        self.show_model_settings()

    def new_file(self):
        """Create a new file"""
        self.text_editor.delete(1.0, tk.END)
        self.status_bar.config(text="New file created")
        
    def open_file(self):
        """Open a file"""
        file_path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[
                ("Python files", "*.py"),
                ("JavaScript files", "*.js"),
                ("HTML files", "*.html"),
                ("CSS files", "*.css"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_editor.delete(1.0, tk.END)
                    self.text_editor.insert(1.0, content)
                    
                # Auto-detect language from extension
                extension = os.path.splitext(file_path)[1].lower()
                language_map = {'.py': 'python', '.js': 'javascript', '.html': 'html', 
                              '.css': 'css', '.java': 'java', '.cpp': 'cpp', '.sql': 'sql'}
                if extension in language_map:
                    self.language_var.set(language_map[extension])
                    
                self.status_bar.config(text=f"Opened: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")
                
    def save_file(self):
        """Save the current file"""
        file_path = filedialog.asksaveasfilename(
            title="Save File",
            defaultextension=".py",
            filetypes=[
                ("Python files", "*.py"),
                ("JavaScript files", "*.js"),
                ("HTML files", "*.html"),
                ("CSS files", "*.css"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.text_editor.get(1.0, tk.END))
                self.status_bar.config(text=f"Saved: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                
    def save_as_file(self):
        """Save as a new file"""
        self.save_file()
        
    def change_api_token(self):
        """Change the API token"""
        self.show_api_token_dialog()
        
    def add_to_chat(self, sender: str, message: str):
        """Add a message to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S")
        
        # Format message with colors
        if sender == "You":
            self.chat_display.insert(tk.END, f"[{timestamp}] You: ", "user")
        elif sender == "Assistant":
            self.chat_display.insert(tk.END, f"[{timestamp}] Assistant: ", "assistant")
        else:
            self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: ", "system")
            
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        # Configure tags for colors
        self.chat_display.tag_config("user", foreground="#0066cc")
        self.chat_display.tag_config("assistant", foreground="#009900")
        self.chat_display.tag_config("system", foreground="#cc6600")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
    def clear_chat(self):
        """Clear the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def send_message(self):
        """Send a message to the AI assistant"""
        user_message = self.chat_input.get(1.0, tk.END).strip()
        if not user_message:
            return
            
        self.chat_input.delete(1.0, tk.END)
        self.add_to_chat("You", user_message)
        
        # Start AI request in a separate thread
        threading.Thread(target=self.process_ai_request, args=(user_message,), daemon=True).start()
        
    def analyze_code(self):
        """Analyze the current code in the editor"""
        code = self.text_editor.get(1.0, tk.END).strip()
        if not code:
            messagebox.showwarning("Warning", "No code to analyze")
            return
            
        language = self.language_var.get()
        message = f"Please analyze this {language} code and provide suggestions for improvement:\n\n{code}"
        self.add_to_chat("You", f"Analyzing current {language} code...")
        
        # Start AI request in a separate thread
        threading.Thread(target=self.process_ai_request, args=(message,), daemon=True).start()
        
    def generate_code(self):
        """Generate code based on user input"""
        description = self.chat_input.get(1.0, tk.END).strip()
        if not description:
            messagebox.showwarning("Warning", "Please enter a description of what you want to generate")
            return
            
        self.chat_input.delete(1.0, tk.END)
        language = self.language_var.get()
        message = f"Generate {language} code for: {description}"
        self.add_to_chat("You", f"Generating {language} code for: {description}")
        
        # Start AI request in a separate thread
        threading.Thread(target=self.process_ai_request, args=(message,), daemon=True).start()
        
    def process_ai_request(self, message: str):
        """Process AI request in a separate thread"""
        try:
            self.root.after(0, lambda: self.status_bar.config(text="Processing AI request..."))
            
            # Prepare the API request
            headers = {
                "Content-Type": "application/json"
            }
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            
            # Use the selected model
            model_url = f"{self.api_url}{self.selected_model}"
            
            # Prepare input based on model type
            if "code" in self.selected_model.lower() or "CodeGPT" in self.selected_model or "CodeBERTa" in self.selected_model:
                # Code-specific models
                data = {
                    "inputs": f"Question: {message}\nAnswer:",
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.7,
                        "do_sample": True,
                        "return_full_text": False
                    }
                }
            elif "DialoGPT" in self.selected_model:
                # DialoGPT models need special format
                data = {
                    "inputs": {
                        "past_user_inputs": [],
                        "generated_responses": [],
                        "text": message
                    },
                    "parameters": {
                        "max_length": 200,
                        "temperature": 0.7
                    }
                }
            elif "blenderbot" in self.selected_model:
                # Blenderbot format
                data = {
                    "inputs": message,
                    "parameters": {
                        "max_length": 200,
                        "temperature": 0.7
                    }
                }
            else:
                # General text generation models
                data = {
                    "inputs": message,
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.7,
                        "do_sample": True,
                        "return_full_text": False
                    }
                }
            
            # Make the API request with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(model_url, headers=headers, json=data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Handle different response formats
                        ai_response = ""
                        
                        if isinstance(result, list) and len(result) > 0:
                            if "generated_text" in result[0]:
                                ai_response = result[0]["generated_text"]
                            elif "response" in result[0]:
                                ai_response = result[0]["response"]
                            else:
                                ai_response = str(result[0])
                        elif isinstance(result, dict):
                            if "generated_text" in result:
                                ai_response = result["generated_text"]
                            elif "response" in result:
                                ai_response = result["response"]
                            else:
                                ai_response = str(result)
                        else:
                            ai_response = str(result)
                        
                        # Clean up response
                        ai_response = ai_response.strip()
                        if not ai_response:
                            ai_response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question or try a different model."
                        
                        # Update UI in main thread
                        self.root.after(0, lambda: self.add_to_chat("Assistant", ai_response))
                        self.root.after(0, lambda: self.status_bar.config(text="AI response received"))
                        
                        # Check if response contains code
                        if any(keyword in ai_response.lower() for keyword in ["def ", "function", "class ", "import", "print", "console.log", "```"]):
                            self.root.after(0, lambda: self.offer_code_insertion(ai_response))
                        
                        return  # Success, exit retry loop
                        
                    elif response.status_code == 503:
                        error_msg = "Model is currently loading, please try again in a few moments."
                        self.root.after(0, lambda: self.add_to_chat("System", error_msg))
                        self.root.after(0, lambda: self.status_bar.config(text="Model loading"))
                        return
                    elif response.status_code == 404:
                        error_msg = f"Model '{self.selected_model}' not found. This might be due to:\n1. Model name changed\n2. Model not available via Inference API\n3. Model requires special permissions\n\nTry clicking the 🔍 button to scan for working models."
                        self.root.after(0, lambda: self.add_to_chat("System", error_msg))
                        self.root.after(0, lambda: self.status_bar.config(text="Model not found"))
                        return
                    elif response.status_code == 401:
                        error_msg = "Authentication failed. Please check your API token."
                        self.root.after(0, lambda: self.add_to_chat("System", error_msg))
                        self.root.after(0, lambda: self.status_bar.config(text="Authentication failed"))
                        return
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            error_msg = f"API Error: {response.status_code} - {response.text}"
                            self.root.after(0, lambda: self.add_to_chat("System", error_msg))
                            self.root.after(0, lambda: self.status_bar.config(text="API request failed"))
                            return
                            
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise e
                        
        except requests.exceptions.Timeout:
            self.root.after(0, lambda: self.add_to_chat("System", "Request timed out. Please try again."))
            self.root.after(0, lambda: self.status_bar.config(text="Request timed out"))
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: self.add_to_chat("System", error_msg))
            self.root.after(0, lambda: self.status_bar.config(text="Error occurred"))
            
    def offer_code_insertion(self, ai_response: str):
        """Offer to insert AI-generated code into the editor"""
        result = messagebox.askyesnocancel(
            "Insert Code", 
            "The AI response appears to contain code. Would you like to:\n\n"
            "• Yes: Replace current editor content\n"
            "• No: Insert at cursor position\n"
            "• Cancel: Do nothing"
        )
        
        if result is not None:  # Not cancelled
            # Extract potential code from response
            code_to_insert = ai_response
            
            if result:  # Yes - replace all
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(1.0, code_to_insert)
                self.status_bar.config(text="Code replaced with AI response")
            else:  # No - insert at cursor
                self.text_editor.insert(tk.INSERT, code_to_insert)
                self.status_bar.config(text="Code inserted at cursor position")
                
    def validate_api_token(self, token: str) -> bool:
        """Validate if the API token is the correct type for Inference API"""
        try:
            # Test the token with a simple API call
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Try to access the Inference API
            response = requests.get(
                "https://api-inference.huggingface.co/models/distilgpt2",
                headers=headers,
                timeout=10
            )
            
            # If we get 200, 503, or even 404, the token is valid for Inference API
            # 404 just means the model doesn't exist, but the token is working
            if response.status_code in [200, 503, 404]:
                return True
            elif response.status_code == 401:
                return False
            else:
                # For any other status, assume it's valid (might be rate limiting, etc.)
                return True
                
        except Exception:
            # If there's an exception, don't assume the token is invalid
            # Just return True and let the actual API call determine if it works
            return True

    def test_connection(self):
        """Test the connection and API token"""
        self.add_to_chat("System", "Testing connection to Hugging Face API...")
        self.status_bar.config(text="Testing connection...")
        
        def test_thread():
            try:
                # Check if we have a token
                if self.api_token:
                    self.root.after(0, lambda: self.add_to_chat("System", f"Using API token: {self.api_token[:10]}..."))
                else:
                    self.root.after(0, lambda: self.add_to_chat("System", "No API token found - testing without authentication"))
                
                # Test with a model that's definitely available
                test_url = f"{self.api_url}distilgpt2"
                headers = {"Content-Type": "application/json"}
                if self.api_token:
                    headers["Authorization"] = f"Bearer {self.api_token}"
                
                test_data = {
                    "inputs": "Hello",
                    "parameters": {
                        "max_new_tokens": 10,
                        "temperature": 0.7
                    }
                }
                
                self.root.after(0, lambda: self.add_to_chat("System", f"Testing URL: {test_url}"))
                response = requests.post(test_url, headers=headers, json=test_data, timeout=15)
                
                self.root.after(0, lambda: self.add_to_chat("System", f"Response status: {response.status_code}"))
                
                if response.status_code == 200:
                    result = response.json()
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        f"✓ Connection successful! API is working properly.\nResponse: {str(result)[:100]}..."))
                    self.root.after(0, lambda: self.status_bar.config(text="Connection successful"))
                elif response.status_code == 503:
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        "✓ Connection successful! Model is loading (this is normal)."))
                    self.root.after(0, lambda: self.status_bar.config(text="Connection successful - model loading"))
                elif response.status_code == 401:
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        "✗ Authentication failed. Please check your API token."))
                    self.root.after(0, lambda: self.status_bar.config(text="Authentication failed"))
                elif response.status_code == 404:
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        f"✗ Model not found. Trying alternative model..."))
                    # Try alternative model
                    alt_url = f"{self.api_url}gpt2"
                    alt_response = requests.post(alt_url, headers=headers, json=test_data, timeout=15)
                    if alt_response.status_code in [200, 503]:
                        self.root.after(0, lambda: self.add_to_chat("System", 
                            f"✓ Alternative model works! Status: {alt_response.status_code}"))
                        self.root.after(0, lambda: self.status_bar.config(text="Connection successful with alternative model"))
                    else:
                        self.root.after(0, lambda: self.add_to_chat("System", 
                            f"✗ Both models failed. Status: {alt_response.status_code}"))
                        self.root.after(0, lambda: self.status_bar.config(text="Connection failed"))
                else:
                    self.root.after(0, lambda: self.add_to_chat("System", 
                        f"✗ Connection failed. Status: {response.status_code}\nResponse: {response.text[:200]}"))
                    self.root.after(0, lambda: self.status_bar.config(text="Connection failed"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.add_to_chat("System", 
                    f"✗ Connection error: {str(e)}"))
                self.root.after(0, lambda: self.status_bar.config(text="Connection error"))
        
        threading.Thread(target=test_thread, daemon=True).start()

    def debug_connection(self):
        """Comprehensive debug of the connection and API"""
        self.add_to_chat("System", "🔍 Starting comprehensive connection debug...")
        self.status_bar.config(text="Debugging connection...")
        
        def debug_thread():
            try:
                # Test 1: Check if we can reach Hugging Face at all
                self.root.after(0, lambda: self.add_to_chat("System", "Test 1: Checking internet connection..."))
                try:
                    response = requests.get("https://huggingface.co", timeout=10)
                    if response.status_code == 200:
                        self.root.after(0, lambda: self.add_to_chat("System", "✓ Internet connection: OK"))
                    else:
                        self.root.after(0, lambda: self.add_to_chat("System", f"✗ Internet connection: Failed (Status: {response.status_code})"))
                        return
                except Exception as e:
                    self.root.after(0, lambda: self.add_to_chat("System", f"✗ Internet connection: Failed - {str(e)}"))
                    return
                
                # Test 2: Check API token format
                if self.api_token:
                    self.root.after(0, lambda: self.add_to_chat("System", f"Test 2: API Token format check..."))
                    if self.api_token.startswith("hf_"):
                        self.root.after(0, lambda: self.add_to_chat("System", "✓ API Token format: Correct (starts with hf_)"))
                    else:
                        self.root.after(0, lambda: self.add_to_chat("System", "⚠️ API Token format: Doesn't start with hf_"))
                else:
                    self.root.after(0, lambda: self.add_to_chat("System", "⚠️ No API token found"))
                
                # Test 3: Test with a simple, definitely working model
                self.root.after(0, lambda: self.add_to_chat("System", "Test 3: Testing with microsoft/DialoGPT-small..."))
                
                test_models = [
                    "microsoft/DialoGPT-small",
                    "distilgpt2", 
                    "gpt2",
                    "EleutherAI/gpt-neo-125M"
                ]
                
                headers = {"Content-Type": "application/json"}
                if self.api_token:
                    headers["Authorization"] = f"Bearer {self.api_token}"
                
                for model in test_models:
                    try:
                        test_url = f"{self.api_url}{model}"
                        self.root.after(0, lambda: self.add_to_chat("System", f"Testing: {model}"))
                        
                        # Test with DialoGPT format for that specific model
                        if "DialoGPT" in model:
                            test_data = {
                                "inputs": {
                                    "past_user_inputs": [],
                                    "generated_responses": [],
                                    "text": "Hello"
                                },
                                "parameters": {
                                    "max_length": 50,
                                    "temperature": 0.7
                                }
                            }
                        else:
                            test_data = {
                                "inputs": "Hello",
                                "parameters": {
                                    "max_new_tokens": 20,
                                    "temperature": 0.7
                                }
                            }
                        
                        response = requests.post(test_url, headers=headers, json=test_data, timeout=15)
                        
                        if response.status_code == 200:
                            result = response.json()
                            self.root.after(0, lambda: self.add_to_chat("System", f"✓ {model}: SUCCESS! Response: {str(result)[:100]}..."))
                            # Found a working model, update the app
                            self.selected_model = model
                            self.model_var.set(model)
                            self.root.after(0, lambda: self.status_bar.config(text=f"Found working model: {model}"))
                            return
                        elif response.status_code == 503:
                            self.root.after(0, lambda: self.add_to_chat("System", f"✓ {model}: Loading (503) - This is normal"))
                        elif response.status_code == 401:
                            self.root.after(0, lambda: self.add_to_chat("System", f"✗ {model}: Authentication failed (401)"))
                        elif response.status_code == 404:
                            self.root.after(0, lambda: self.add_to_chat("System", f"✗ {model}: Not found (404)"))
                        else:
                            self.root.after(0, lambda: self.add_to_chat("System", f"✗ {model}: Failed (Status: {response.status_code})"))
                            
                    except Exception as e:
                        self.root.after(0, lambda: self.add_to_chat("System", f"✗ {model}: Error - {str(e)}"))
                
                # Test 4: Try without authentication
                self.root.after(0, lambda: self.add_to_chat("System", "Test 4: Testing without authentication..."))
                try:
                    test_url = f"{self.api_url}distilgpt2"
                    test_data = {
                        "inputs": "Hello",
                        "parameters": {
                            "max_new_tokens": 10,
                            "temperature": 0.7
                        }
                    }
                    
                    response = requests.post(test_url, json=test_data, timeout=15)
                    if response.status_code in [200, 503]:
                        self.root.after(0, lambda: self.add_to_chat("System", f"✓ Works without authentication! Status: {response.status_code}"))
                    else:
                        self.root.after(0, lambda: self.add_to_chat("System", f"✗ Doesn't work without authentication. Status: {response.status_code}"))
                        
                except Exception as e:
                    self.root.after(0, lambda: self.add_to_chat("System", f"✗ Error testing without auth: {str(e)}"))
                
                # Final summary
                self.root.after(0, lambda: self.add_to_chat("System", 
                    "🔍 Debug Summary:\n"
                    "If no models worked, try:\n"
                    "1. Check your internet connection\n"
                    "2. Verify your API token has 'Inference' permissions\n"
                    "3. Try the 'Scan for Working Models' button\n"
                    "4. Some models may be temporarily unavailable"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.add_to_chat("System", f"✗ Debug error: {str(e)}"))
        
        threading.Thread(target=debug_thread, daemon=True).start()

    def run(self):
        """Start the application"""
        self.root.mainloop()

# Tooltip class for hover information
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="#ffffe0", 
                        relief="solid", borderwidth=1, padx=5, pady=3)
        label.pack()

    def leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

if __name__ == "__main__":
    app = HuggingFaceCodeEditor()
    app.run()
