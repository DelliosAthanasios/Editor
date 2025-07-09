#!/usr/bin/env python3
"""
Programming Language Scanner - Enhanced Edition
A safe, lightweight scanner for detecting programming languages with improved UI and scanning capabilities
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import time
from datetime import datetime
import signal
import string
import platform
import re
import webbrowser
from collections import defaultdict
import threading

class EnhancedLanguageScanner:
    def __init__(self):
        # Expanded known executables with better categorization
        self.known_executables = {
            'python': 'Python', 'python3': 'Python', 'py': 'Python', 
            'java': 'Java', 'javac': 'Java', 'jshell': 'Java',
            'node': 'JavaScript', 'npm': 'JavaScript', 'npx': 'JavaScript', 'yarn': 'JavaScript',
            'gcc': 'C', 'g++': 'C++', 'clang': 'C/C++', 'clang++': 'C++',
            'go': 'Go', 'gofmt': 'Go', 
            'rustc': 'Rust', 'cargo': 'Rust',
            'php': 'PHP', 'composer': 'PHP',
            'ruby': 'Ruby', 'gem': 'Ruby', 'rake': 'Ruby',
            'perl': 'Perl', 
            'make': 'Build Tools', 'cmake': 'Build Tools', 'ninja': 'Build Tools',
            'git': 'Version Control', 'svn': 'Version Control', 'hg': 'Version Control',
            'code': 'Editors', 'vim': 'Editors', 'nano': 'Editors', 'subl': 'Editors',
            'dotnet': '.NET', 'dart': 'Dart', 'swift': 'Swift', 'kotlin': 'Kotlin',
            'gradle': 'Build Tools', 'mvn': 'Build Tools', 'pod': 'iOS/MacOS', 
            'tsc': 'TypeScript', 'eslint': 'JavaScript', 'prettier': 'Formatters',
            'pip': 'Python', 'conda': 'Python', 'poetry': 'Python',
            'docker': 'Containers', 'docker-compose': 'Containers', 'kubectl': 'Containers',
            'terraform': 'Infrastructure', 'ansible': 'Infrastructure',
            'pandoc': 'Documentation', 'jupyter': 'Data Science',
            'sqlite3': 'Databases', 'psql': 'Databases', 'mysql': 'Databases'
        }
        
        # Enhanced file extensions with better categorization
        self.file_extensions = {
            # Programming Languages
            '.py': 'Python', '.java': 'Java', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.c': 'C', '.cpp': 'C++', '.h': 'C/C++', '.hpp': 'C++', '.cs': 'C#', '.go': 'Go',
            '.rs': 'Rust', '.php': 'PHP', '.rb': 'Ruby', '.pl': 'Perl', '.swift': 'Swift',
            '.kt': 'Kotlin', '.dart': 'Dart', '.scala': 'Scala', '.hs': 'Haskell', 
            '.lua': 'Lua', '.r': 'R', '.jl': 'Julia', '.fs': 'F#', '.vb': 'VB.NET',
            '.asm': 'Assembly', '.s': 'Assembly', '.ex': 'Elixir', '.exs': 'Elixir',
            '.erl': 'Erlang', '.hrl': 'Erlang', '.clj': 'Clojure', '.cljs': 'ClojureScript',
            '.coffee': 'CoffeeScript',
            
            # Web Technologies
            '.html': 'HTML', '.htm': 'HTML', '.xhtml': 'HTML', '.css': 'CSS', '.scss': 'CSS', 
            '.less': 'CSS', '.sass': 'CSS', '.vue': 'Vue', '.svelte': 'Svelte', '.elm': 'Elm',
            '.jsx': 'React', '.tsx': 'React', '.ejs': 'EJS',
            
            # Configuration & Data
            '.json': 'JSON', '.xml': 'XML', '.yaml': 'YAML', '.yml': 'YAML', '.toml': 'TOML',
            '.ini': 'Configuration', '.cfg': 'Configuration', '.conf': 'Configuration',
            '.env': 'Configuration', '.properties': 'Configuration',
            '.sql': 'SQL', '.csv': 'Data', '.tsv': 'Data',
            
            # Documentation
            '.md': 'Markdown', '.rst': 'reStructuredText', '.tex': 'LaTeX', 
            '.txt': 'Text', '.log': 'Logs',
            
            # Build & Package Management
            '.lock': 'Dependency Lock', '.sum': 'Dependency Checksum',
            
            # Scripts
            '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell', '.fish': 'Shell',
            '.bat': 'Batch', '.cmd': 'Batch', '.ps1': 'PowerShell',
            
            # Other
            '.dockerfile': 'Docker', '.Dockerfile': 'Docker',
            '.tf': 'Terraform', '.tfvars': 'Terraform',
            '.ipynb': 'Jupyter Notebook'
        }
        
        # Enhanced directory indicators with better categorization
        self.safe_directories = {
            # Source Code
            'src': 'Source Code', 'source': 'Source Code', 'lib': 'Libraries', 
            'include': 'Libraries', 'libs': 'Libraries',
            
            # Project Structure
            'docs': 'Documentation', 'doc': 'Documentation', 'examples': 'Examples',
            'samples': 'Examples', 'demo': 'Examples', 
            'test': 'Tests', 'tests': 'Tests', 'spec': 'Tests', '__tests__': 'Tests',
            'bin': 'Binaries', 'build': 'Build Output', 'dist': 'Distribution', 
            'out': 'Build Output', 'target': 'Build Output', 'obj': 'Build Output',
            
            # Dependency Management
            'node_modules': 'JavaScript', 'vendor': 'PHP', 'pods': 'iOS/MacOS', 
            '__pycache__': 'Python', '.venv': 'Python', 'venv': 'Python',
            '.mypy_cache': 'Python', '.pytest_cache': 'Python',
            
            # Version Control & CI/CD
            '.git': 'Version Control', '.svn': 'Version Control', '.hg': 'Version Control',
            '.github': 'CI/CD', '.circleci': 'CI/CD', '.travis': 'CI/CD', 
            '.azure-pipelines': 'CI/CD', '.gitlab-ci': 'CI/CD',
            
            # IDE & Editor Config
            '.vscode': 'VS Code', '.idea': 'JetBrains IDE', '.vs': 'Visual Studio', 
            '.settings': 'Eclipse', '.project': 'Eclipse',
            
            # Package Management
            'packages': 'NuGet', 'gradle': 'Gradle', '.cargo': 'Rust',
            
            # Configuration
            'config': 'Configuration', 'conf': 'Configuration', 'settings': 'Configuration',
            
            # Environment Specific
            'docker': 'Docker', 'deploy': 'Deployment', 'infra': 'Infrastructure',
            'terraform': 'Infrastructure', 'ansible': 'Infrastructure',
            
            # Data & Assets
            'data': 'Data', 'assets': 'Assets', 'static': 'Static Assets', 'public': 'Public Assets',
            'resources': 'Resources',
            
            # Documentation
            'wiki': 'Documentation', 'man': 'Documentation'
        }
        
        # Special files that indicate projects/languages with better categorization
        self.special_files = {
            # Package Managers
            'package.json': 'JavaScript', 'package-lock.json': 'JavaScript', 
            'yarn.lock': 'JavaScript', 'pnpm-lock.yaml': 'JavaScript',
            'requirements.txt': 'Python', 'Pipfile': 'Python', 'pyproject.toml': 'Python',
            'poetry.lock': 'Python', 'setup.py': 'Python',
            'pom.xml': 'Java', 'build.gradle': 'Java', 'build.gradle.kts': 'Java',
            'Cargo.toml': 'Rust', 'Cargo.lock': 'Rust',
            'go.mod': 'Go', 'go.sum': 'Go',
            'composer.json': 'PHP', 'composer.lock': 'PHP',
            'Gemfile': 'Ruby', 'Gemfile.lock': 'Ruby',
            'Podfile': 'iOS/MacOS', 'Cartfile': 'iOS/MacOS',
            'pubspec.yaml': 'Dart', 'pubspec.lock': 'Dart',
            
            # Configuration Files
            '.gitignore': 'Version Control', '.gitattributes': 'Version Control',
            '.gitmodules': 'Version Control', '.gitconfig': 'Version Control',
            'docker-compose.yml': 'Docker', 'docker-compose.yaml': 'Docker',
            'Makefile': 'Build Tools', 'CMakeLists.txt': 'Build Tools',
            'tsconfig.json': 'TypeScript', 'jsconfig.json': 'JavaScript',
            'webpack.config.js': 'JavaScript', 'rollup.config.js': 'JavaScript',
            '.eslintrc': 'JavaScript', '.prettierrc': 'Formatters',
            '.babelrc': 'JavaScript',
            
            # Documentation
            'README.md': 'Documentation', 'README.txt': 'Documentation', 
            'README': 'Documentation', 'LICENSE': 'Documentation', 
            'CHANGELOG.md': 'Documentation', 'CONTRIBUTING.md': 'Documentation',
            
            # Environment Files
            '.env': 'Configuration', '.env.example': 'Configuration',
            '.env.local': 'Configuration', '.env.dev': 'Configuration',
            
            # Project Files
            'project.json': 'Project Configuration', 'workspace.json': 'Project Configuration',
            'BUILD': 'Bazel', 'WORKSPACE': 'Bazel',
            
            # Infrastructure
            'terraform.tf': 'Terraform', 'terraform.tfvars': 'Terraform',
            'main.tf': 'Terraform', 'variables.tf': 'Terraform',
            
            # CI/CD
            '.gitlab-ci.yml': 'CI/CD', '.travis.yml': 'CI/CD', 'azure-pipelines.yml': 'CI/CD',
            'circle.yml': 'CI/CD', 'Jenkinsfile': 'CI/CD',
            
            # Notebooks
            '*.ipynb': 'Jupyter Notebook'
        }
        
        # Language categories for better organization
        self.language_categories = {
            'Python': 'Programming Languages',
            'Java': 'Programming Languages',
            'JavaScript': 'Programming Languages',
            'TypeScript': 'Programming Languages',
            'C': 'Programming Languages',
            'C++': 'Programming Languages',
            'C#': 'Programming Languages',
            'Go': 'Programming Languages',
            'Rust': 'Programming Languages',
            'PHP': 'Programming Languages',
            'Ruby': 'Programming Languages',
            'Perl': 'Programming Languages',
            'Swift': 'Programming Languages',
            'Kotlin': 'Programming Languages',
            'Dart': 'Programming Languages',
            'HTML': 'Web Technologies',
            'CSS': 'Web Technologies',
            'Vue': 'Web Technologies',
            'React': 'Web Technologies',
            'Svelte': 'Web Technologies',
            'JSON': 'Data Formats',
            'XML': 'Data Formats',
            'YAML': 'Data Formats',
            'TOML': 'Data Formats',
            'SQL': 'Data Formats',
            'Markdown': 'Documentation',
            'Text': 'Documentation',
            'reStructuredText': 'Documentation',
            'LaTeX': 'Documentation',
            'Shell': 'Scripting',
            'Batch': 'Scripting',
            'PowerShell': 'Scripting',
            'Docker': 'Containers',
            'Terraform': 'Infrastructure',
            'Jupyter Notebook': 'Data Science',
            'Build Tools': 'Development Tools',
            'Version Control': 'Development Tools',
            'VS Code': 'Development Tools',
            'JetBrains IDE': 'Development Tools',
            'Visual Studio': 'Development Tools',
            'CI/CD': 'Development Tools',
            'Configuration': 'Configuration',
            'Documentation': 'Documentation',
            'Tests': 'Testing',
            'Source Code': 'Project Structure',
            'Libraries': 'Project Structure',
            'Binaries': 'Project Structure',
            'Build Output': 'Project Structure',
            'Distribution': 'Project Structure',
            'Examples': 'Project Structure',
            'Data': 'Resources',
            'Assets': 'Resources',
            'Static Assets': 'Resources',
            'Public Assets': 'Resources',
            'Resources': 'Resources'
        }
        
        self.found_languages = defaultdict(list)
        self.scan_cancelled = False
        self.scanning = False
        self.scan_stats = {'files_scanned': 0, 'directories_scanned': 0, 'start_time': 0}
        
        # Rate limiting to avoid suspicious behavior
        self.last_scan_time = 0
        self.min_scan_interval = 1  # Minimum 1 second between scans
        
    def get_all_drives(self):
        """Get all available drives on the system"""
        drives = []
        if platform.system() == "Windows":
            # Get drive letters
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        else:
            # For Unix-based systems, scan common mount points
            drives.append("/")
            if os.path.exists("/mnt"):
                for entry in os.listdir("/mnt"):
                    path = os.path.join("/mnt", entry)
                    if os.path.isdir(path):
                        drives.append(path)
            if os.path.exists("/Volumes"):  # macOS
                for entry in os.listdir("/Volumes"):
                    path = os.path.join("/Volumes", entry)
                    if os.path.isdir(path):
                        drives.append(path)
        return drives
        
    def is_safe_to_scan(self):
        """Check if it's safe to start scanning"""
        current_time = time.time()
        if current_time - self.last_scan_time < self.min_scan_interval:
            return False
        return True
    
    def safe_check_executable(self, exe_name):
        """Safely check if an executable exists without running it"""
        try:
            # Only check if executable exists, don't run it
            import shutil
            path = shutil.which(exe_name)
            if path and os.path.exists(path):
                # Try to get version information safely
                version_info = 'Found'
                try:
                    if platform.system() == "Windows":
                        version_info = self.get_windows_file_version(path)
                    else:
                        # On Unix systems, try to get version through --version
                        result = subprocess.run(
                            [path, '--version'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=1
                        )
                        if result.returncode == 0:
                            version_lines = result.stdout.split('\n')
                            version_info = version_lines[0].strip() if version_lines else 'Found'
                except Exception:
                    pass
                
                return {
                    'executable': exe_name,
                    'path': path,
                    'version': version_info
                }
        except Exception:
            pass
        return None
    
    def get_windows_file_version(self, path):
        """Get file version information on Windows"""
        try:
            from win32api import GetFileVersionInfo, LOWORD, HIWORD
            info = GetFileVersionInfo(path, "\\")
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            return f"{HIWORD(ms)}.{LOWORD(ms)}.{HIWORD(ls)}.{LOWORD(ls)}"
        except ImportError:
            try:
                # Fallback for systems without pywin32
                import winreg
                import struct
                
                # Read version from registry
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        name = winreg.EnumKey(key, i)
                        if name.lower() == os.path.basename(path).lower():
                            with winreg.OpenKey(key, name) as subkey:
                                value = winreg.QueryValue(subkey, None)
                                if os.path.exists(value):
                                    return "Found (registry)"
            except Exception:
                pass
        except Exception:
            pass
        return "Found"
    
    def scan_path_safely(self):
        """Safely scan PATH for known executables"""
        found = defaultdict(list)
        
        # Only check predefined safe executables
        for exe_name, lang_name in self.known_executables.items():
            if self.scan_cancelled:
                break
                
            result = self.safe_check_executable(exe_name)
            if result:
                found[lang_name].append(result)
            
            # Small delay to avoid appearing suspicious
            time.sleep(0.05)
        
        return found
    
    def matches_pattern(self, filename, pattern):
        """Check if filename matches a pattern with wildcards"""
        if '*' in pattern:
            regex = re.compile(pattern.replace('.', r'\.').replace('*', '.*'))
            return bool(regex.match(filename))
        return filename == pattern
    
    def scan_directory_safely(self, directory, max_files=300):
        """Safely scan directory with limits"""
        found = defaultdict(list)
        file_count = 0
        self.scan_stats['directories_scanned'] += 1
        
        try:
            # Ask for permission first
            if not os.access(directory, os.R_OK):
                return found
                
            for root, dirs, files in os.walk(directory):
                if self.scan_cancelled or file_count >= max_files:
                    break
                
                # Check directory names
                for dirname in dirs:
                    if dirname in self.safe_directories:
                        lang = self.safe_directories[dirname]
                        found[lang].append({
                            'type': 'directory',
                            'path': os.path.join(root, dirname),
                            'indicator': dirname
                        })
                
                # Check special files
                for filename in files:
                    if self.scan_cancelled:
                        break
                        
                    for pattern, lang in self.special_files.items():
                        if self.matches_pattern(filename, pattern):
                            # Only add if not already present
                            if not any(item.get('type') == 'special_file' and 
                                     os.path.basename(item.get('path', '')) == filename 
                                     for item in found[lang]):
                                found[lang].append({
                                    'type': 'special_file',
                                    'filename': filename,
                                    'path': os.path.join(root, filename)
                                })
                            break  # Only match one pattern per file
                
                # Check file extensions (limited)
                for filename in files[:40]:  # Limit files per directory
                    if self.scan_cancelled:
                        break
                        
                    file_count += 1
                    self.scan_stats['files_scanned'] += 1
                    if file_count >= max_files:
                        break
                        
                    _, ext = os.path.splitext(filename)
                    ext = ext.lower()
                    if ext in self.file_extensions:
                        lang = self.file_extensions[ext]
                        # Only add if not already present
                        if not any(item.get('type') == 'file_extension' and 
                                 item.get('extension') == ext 
                                 for item in found[lang]):
                            found[lang].append({
                                'type': 'file_extension',
                                'extension': ext,
                                'example_file': os.path.join(root, filename)
                            })
                
                # Don't go too deep
                if len(root.split(os.sep)) - len(directory.split(os.sep)) > 3:
                    dirs.clear()
                    
        except (PermissionError, OSError):
            pass
        
        return found
    
    def scan_all(self, custom_directories=None):
        """Main scanning function with safety measures"""
        if not self.is_safe_to_scan():
            if hasattr(self, 'status_var'):
                self.status_var.set("Please wait before scanning again...")
            return
        
        self.scanning = True
        self.scan_cancelled = False
        self.found_languages = defaultdict(list)
        self.last_scan_time = time.time()
        self.scan_stats = {
            'files_scanned': 0, 
            'directories_scanned': 0,
            'start_time': time.time(),
            'languages_found': 0
        }
        
        try:
            # 1. Scan PATH for executables
            if hasattr(self, 'status_var'):
                self.status_var.set("Checking installed tools...")
            
            path_languages = self.scan_path_safely()
            
            # 2. Scan user-specified directories only
            scan_dirs = custom_directories or []
            
            # Add disk roots if scanning all disks
            if hasattr(self, 'scan_all_disks') and self.scan_all_disks.get():
                scan_dirs.extend(self.get_all_drives())
            
            # Add user directories if requested
            if hasattr(self, 'scan_user_dirs') and self.scan_user_dirs.get():
                scan_dirs.extend([
                    os.path.expanduser('~/Documents'),
                    os.path.expanduser('~/Desktop'),
                    os.path.expanduser('~/Downloads'),
                    os.path.expanduser('~/Projects'),
                    os.path.expanduser('~/workspace'),
                    os.path.expanduser('~/src'),
                    os.path.expanduser('~/git'),
                    os.path.expanduser('~/code')
                ])
            
            # Remove duplicates and non-existing directories
            scan_dirs = list(set(scan_dirs))
            scan_dirs = [d for d in scan_dirs if os.path.exists(d)]
            
            total_dirs = len(scan_dirs)
            for i, directory in enumerate(scan_dirs):
                if self.scan_cancelled:
                    break
                if hasattr(self, 'status_var'):
                    self.status_var.set(f"Scanning ({i+1}/{total_dirs}): {os.path.basename(directory)}")
                
                dir_languages = self.scan_directory_safely(directory)
                
                # Merge results
                for lang, items in dir_languages.items():
                    path_languages[lang].extend(items)
                
                # Small delay between directories
                time.sleep(0.2)
            
            # Categorize and sort results
            categorized = defaultdict(list)
            for lang, items in path_languages.items():
                category = self.language_categories.get(lang, "Other")
                categorized[category].append((lang, items))
            
            # Sort categories and languages
            sorted_categories = sorted(categorized.keys())
            for category in sorted_categories:
                languages = sorted(categorized[category], key=lambda x: x[0])
                for lang, items in languages:
                    self.found_languages[lang] = items
            
            self.scan_stats['languages_found'] = len(self.found_languages)
            
        except Exception as e:
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Error during scan: {str(e)}")
        finally:
            self.scanning = False
            duration = time.time() - self.scan_stats['start_time']
            if hasattr(self, 'status_var'):
                self.status_var.set(
                    f"Scan complete! Found {self.scan_stats['languages_found']} languages "
                    f"({self.scan_stats['files_scanned']} files, "
                    f"{self.scan_stats['directories_scanned']} dirs, "
                    f"{duration:.1f} sec)"
                )
    
    def create_gui(self):
        """Create enhanced, user-friendly GUI"""
        self.root = tk.Tk()
        self.root.title("Enhanced Language Scanner")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # Set application icon if available
        try:
            self.root.iconbitmap(default='python.ico')
        except:
            pass
        
        # Configure style
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 10))
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('Treeview', rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 15))
        
        title_label = ttk.Label(header_frame, text="Enhanced Language Scanner", 
                               style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(header_frame, 
                                  text="Comprehensive detection of programming languages and development tools",
                                  style='Subtitle.TLabel')
        subtitle_label.pack(pady=(5, 0))
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Scan Options", padding="10")
        options_frame.pack(fill='x', pady=(0, 10))
        
        # Options grid
        options_grid = ttk.Frame(options_frame)
        options_grid.pack(fill='x')
        
        # Scan options
        ttk.Label(options_grid, text="Scan Scope:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        
        self.scan_user_dirs = tk.BooleanVar(value=True)
        user_dirs_check = ttk.Checkbutton(options_grid, 
                                         text="User directories",
                                         variable=self.scan_user_dirs)
        user_dirs_check.grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        self.scan_all_disks = tk.BooleanVar(value=False)
        all_disks_check = ttk.Checkbutton(options_grid, 
                                         text="All disks",
                                         variable=self.scan_all_disks)
        all_disks_check.grid(row=0, column=2, sticky='w')
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x')
        
        self.scan_button = ttk.Button(button_frame, text="Start Scan", 
                                     command=self.start_safe_scan, width=12)
        self.scan_button.pack(side='left', padx=(0, 8))
        
        self.folder_button = ttk.Button(button_frame, text="Add Folder", 
                                       command=self.add_custom_folder, width=12)
        self.folder_button.pack(side='left', padx=(0, 8))
        
        self.clear_button = ttk.Button(button_frame, text="Clear Folders", 
                                      command=self.clear_custom_folders, width=12)
        self.clear_button.pack(side='left', padx=(0, 8))
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", 
                                       command=self.cancel_scan, state='disabled', width=12)
        self.cancel_button.pack(side='left', padx=(0, 8))
        
        self.save_button = ttk.Button(button_frame, text="Save Results", 
                                     command=self.save_results, width=12)
        self.save_button.pack(side='right', padx=(0, 8))
        
        self.expand_button = ttk.Button(button_frame, text="Expand All", 
                                       command=self.expand_all, width=12)
        self.expand_button.pack(side='right', padx=(0, 8))
        
        self.collapse_button = ttk.Button(button_frame, text="Collapse All", 
                                         command=self.collapse_all, width=12)
        self.collapse_button.pack(side='right', padx=(0, 8))
        
        # Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill='x', pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready to scan")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                style='Status.TLabel')
        status_label.pack(side='left')
        
        # Progress
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=200)
        self.progress.pack(side='right')
        
        # Custom directories
        self.custom_dirs_frame = ttk.LabelFrame(main_frame, text="Custom Directories", padding="10")
        self.custom_dirs_frame.pack(fill='x', pady=(0, 10))
        
        self.custom_dirs_text = scrolledtext.ScrolledText(
            self.custom_dirs_frame, height=3, wrap='word', font=('Arial', 9)
        )
        self.custom_dirs_text.pack(fill='x')
        self.custom_dirs_text.insert('1.0', 'No custom directories added yet.')
        self.custom_dirs_text.config(state='disabled')
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Scan Results", padding="10")
        results_frame.pack(fill='both', expand=True)
        
        # Create a treeview with scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill='both', expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=('Type', 'Path', 'Info'), 
                                show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='Language/Tool', anchor='w')
        self.tree.heading('Type', text='Detection Method', anchor='w')
        self.tree.heading('Path', text='Location', anchor='w')
        self.tree.heading('Info', text='Details', anchor='w')
        
        self.tree.column('#0', width=200, minwidth=150, anchor='w')
        self.tree.column('Type', width=150, minwidth=120, anchor='w')
        self.tree.column('Path', width=350, minwidth=200, anchor='w')
        self.tree.column('Info', width=250, minwidth=150, anchor='w')
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Add context menu
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Copy Path", command=self.copy_selected_path)
        self.tree_menu.add_command(label="Open in File Explorer", command=self.open_in_explorer)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Collapse All", command=self.collapse_all)
        self.tree_menu.add_command(label="Expand All", command=self.expand_all)
        self.tree.bind("<Button-3>", self.show_tree_context_menu)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        # Custom directories list
        self.custom_directories = []
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Add help menu
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_docs)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)
        
        # Set focus to scan button
        self.scan_button.focus_set()
        
        return self.root
    
    def show_tree_context_menu(self, event):
        """Show context menu for tree items"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)
    
    def copy_selected_path(self):
        """Copy selected path to clipboard"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            if values and len(values) >= 2:  # Path is in the second column
                path = values[1]
                self.root.clipboard_clear()
                self.root.clipboard_append(path)
                self.status_var.set("Path copied to clipboard")
    
    def open_in_explorer(self):
        """Open selected path in file explorer"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            if values and len(values) >= 2:  # Path is in the second column
                path = values[1]
                if os.path.exists(path):
                    if platform.system() == "Windows":
                        os.startfile(os.path.dirname(path))
                    elif platform.system() == "Darwin":
                        subprocess.Popen(["open", os.path.dirname(path)])
                    else:
                        subprocess.Popen(["xdg-open", os.path.dirname(path)])
                    self.status_var.set("Opened in file explorer")
                else:
                    self.status_var.set("Path does not exist")
    
    def on_tree_double_click(self, event):
        """Handle double click on tree item"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            self.open_in_explorer()
    
    def expand_all(self):
        """Expand all tree items"""
        for item in self.tree.get_children():
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                self.tree.item(child, open=True)
    
    def collapse_all(self):
        """Collapse all tree items"""
        for item in self.tree.get_children():
            self.tree.item(item, open=False)
    
    def add_custom_folder(self):
        """Add custom folder with user confirmation"""
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if folder:
            # Ask for confirmation
            if messagebox.askyesno("Confirm", f"Add folder for scanning?\n\n{folder}"):
                self.custom_directories.append(folder)
                self.update_custom_dirs_display()
                self.status_var.set(f"Added folder: {os.path.basename(folder)}")
    
    def clear_custom_folders(self):
        """Clear all custom folders"""
        if self.custom_directories:
            if messagebox.askyesno("Confirm", "Remove all custom folders?"):
                self.custom_directories = []
                self.update_custom_dirs_display()
                self.status_var.set("Custom folders cleared")
        else:
            self.status_var.set("No custom folders to clear")
    
    def update_custom_dirs_display(self):
        """Update custom directories display"""
        self.custom_dirs_text.config(state='normal')
        self.custom_dirs_text.delete('1.0', tk.END)
        
        if self.custom_directories:
            for i, directory in enumerate(self.custom_directories, 1):
                self.custom_dirs_text.insert(tk.END, f"{i}. {directory}\n")
        else:
            self.custom_dirs_text.insert(tk.END, "No custom directories added yet.")
        
        self.custom_dirs_text.config(state='disabled')
    
    def start_safe_scan(self):
        """Start scanning with safety measures"""
        if self.scanning:
            return
        
        # Confirmation dialog
        if not messagebox.askyesno("Confirm Scan", 
                                  "Start scanning for programming languages and tools?\n\n" +
                                  "This will safely check for installed tools and " +
                                  "examine file extensions in selected directories."):
            return
        
        self.scan_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.progress.start()
        
        def scan_thread():
            try:
                self.scan_all(self.custom_directories)
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
            finally:
                self.root.after(0, self.scan_finished)
                self.root.after(0, self.update_results)
        
        self.scan_thread = threading.Thread(target=scan_thread, daemon=True)
        self.scan_thread.start()
    
    def cancel_scan(self):
        """Cancel current scan"""
        self.scan_cancelled = True
        self.scan_finished()
        self.status_var.set("Scan cancelled by user")
    
    def scan_finished(self):
        """Clean up after scan"""
        self.progress.stop()
        self.scan_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.scanning = False
    
    def update_results(self):
        """Update results display"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.found_languages:
            self.tree.insert('', 'end', text='No languages detected', values=('', '', ''))
            return
        
        # Add results with categories
        for lang, items in self.found_languages.items():
            category = self.language_categories.get(lang, "Other")
            category_item = self.tree.insert('', 'end', text=category, open=True)
            lang_item = self.tree.insert(category_item, 'end', text=lang, open=True)
            
            for item in items:
                item_type = item.get('type', 'executable')
                if item_type == 'executable':
                    self.tree.insert(lang_item, 'end', text='',
                                   values=('Executable', item.get('path', ''), 
                                          item.get('version', '')))
                elif item_type == 'file_extension':
                    self.tree.insert(lang_item, 'end', text='',
                                   values=('File Extension', item.get('example_file', ''), 
                                          item.get('extension', '')))
                elif item_type == 'directory':
                    self.tree.insert(lang_item, 'end', text='',
                                   values=('Directory', item.get('path', ''), 
                                          item.get('indicator', '')))
                elif item_type == 'special_file':
                    self.tree.insert(lang_item, 'end', text='',
                                   values=('Special File', item.get('path', ''), 
                                          item.get('filename', '')))
    
    def save_results(self):
        """Save results to file"""
        if not self.found_languages:
            messagebox.showwarning("No Data", "No results to save. Please run a scan first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"), 
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"), 
                ("All files", "*.*")
            ],
            title="Save Scan Results"
        )
        
        if not filename:
            return
        
        try:
            data = {
                'scan_date': datetime.now().isoformat(),
                'scanner_version': '4.0',
                'scan_stats': self.scan_stats,
                'custom_directories': self.custom_directories,
                'scan_options': {
                    'user_directories': self.scan_user_dirs.get(),
                    'scan_all_disks': self.scan_all_disks.get()
                },
                'languages': self.found_languages
            }
            
            if filename.endswith('.json'):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            elif filename.endswith('.csv'):
                import csv
                with open(filename, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Category', 'Language/Tool', 'Detection Method', 'Path', 'Details'])
                    
                    for lang, items in self.found_languages.items():
                        category = self.language_categories.get(lang, "Other")
                        for item in items:
                            writer.writerow([
                                category,
                                lang,
                                item.get('type', ''),
                                item.get('path', item.get('example_file', '')),
                                item.get('version', item.get('extension', item.get('indicator', '')))
                            ])
            
            else:  # Text format
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Language Scanner Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"Scan Duration: {time.time() - self.scan_stats['start_time']:.2f} seconds\n")
                    f.write(f"Files Scanned: {self.scan_stats['files_scanned']}\n")
                    f.write(f"Directories Scanned: {self.scan_stats['directories_scanned']}\n")
                    f.write(f"Languages/Tools Found: {self.scan_stats['languages_found']}\n\n")
                    
                    for lang, items in self.found_languages.items():
                        category = self.language_categories.get(lang, "Other")
                        f.write(f"{category} > {lang}:\n")
                        for item in items:
                            if item.get('type') == 'executable':
                                f.write(f"  [Executable] {item.get('path')} ({item.get('version')})\n")
                            elif item.get('type') == 'file_extension':
                                f.write(f"  [File Extension] {item.get('example_file')} ({item.get('extension')})\n")
                            elif item.get('type') == 'directory':
                                f.write(f"  [Directory] {item.get('path')}\n")
                            elif item.get('type') == 'special_file':
                                f.write(f"  [Special File] {item.get('path')}\n")
                        f.write("\n")
            
            self.status_var.set(f"Results saved to {os.path.basename(filename)}")
            messagebox.showinfo("Success", f"Results saved to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = (
            "Enhanced Language Scanner\n"
            "Version 4.0\n\n"
            "A comprehensive tool for detecting programming languages, "
            "development tools, and project structures on your system.\n\n"
            "Features:\n"
            "- Safe scanning without executing untrusted code\n"
            "- Detection based on executables, file extensions, directories, and special files\n"
            "- Categorized results for better organization\n"
            "- Export to JSON, CSV, or text formats\n\n"
            "© 2025 Developer Tools Project"
        )
        messagebox.showinfo("About", about_text)
    
    def show_docs(self):
        """Open documentation in browser"""
        docs_url = "https://github.com/devtools/langscanner/docs"
        webbrowser.open(docs_url)
    
    def on_closing(self):
        """Handle window close event"""
        if self.scanning:
            if messagebox.askyesno("Confirm Exit", "Scan in progress. Cancel and exit?"):
                self.scan_cancelled = True
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.create_gui()
        self.root.mainloop()

def main():
    """Main entry point"""
    print("Enhanced Language Scanner v4.0")
    print("Comprehensive detection of programming languages and tools")
    print("-" * 60)
    
    # Add signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\nShutting down safely...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        scanner = EnhancedLanguageScanner()
        scanner.run()
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()