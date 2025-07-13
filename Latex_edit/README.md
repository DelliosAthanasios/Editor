# LaTeX Editor Environment

A comprehensive LaTeX editing environment for Third Edit, inspired by TeXstudio, with full integration into the main editor.

## Features

### Core LaTeX Features
- **Compiler Detection**: Automatically finds pdflatex/xelatex/lualatex on startup
- **Real-time Compilation**: Run LaTeX with F5, stop with F6
- **Output Panel**: Shows compilation output and errors with syntax highlighting
- **Multiple Compilers**: Switch between pdflatex, xelatex, and lualatex

### Editor Features
- **Syntax Highlighting**: LaTeX commands, comments, math mode, and braces
- **Auto-completion**: Suggests LaTeX commands as you type
- **Number Line**: Line numbers with theme support
- **Minimap**: Code overview and navigation
- **Search & Replace**: Advanced search with result navigation
- **Dynamic Saving**: Auto-saves changes with configurable intervals

### UI & Layout
- **Modern Interface**: Clean, professional design matching the main editor
- **Resizable Panels**: Adjust editor and output panel sizes
- **Layout Switching**: Toggle between vertical and horizontal layouts
- **Collapsible Panels**: Hide/show numberline, minimap, and output
- **Theme Integration**: Follows main editor's theme system

### File Operations
- **Full File Menu**: New, Open, Save, Save As with keyboard shortcuts
- **Tab Integration**: Opens as a tab in the main editor
- **File Path Management**: Proper file path handling and display
- **Modified Indicators**: Shows when files have unsaved changes

### Main Editor Integration
- **Menu Integration**: All File/Edit/View actions work seamlessly
- **Keyboard Shortcuts**: Standard shortcuts (Ctrl+S, Ctrl+O, etc.)
- **Theme Support**: Automatically applies main editor themes
- **Dynamic Saving**: Integrated with main editor's saving system
- **Search Integration**: Works with main editor's search functionality

### Toolbar & Quick Actions
- **File Operations**: New, Open, Save buttons
- **LaTeX Actions**: Run (▶), Stop (⏹) buttons
- **Formatting**: Bold (B), Italic (I), Section (§) quick insert
- **Compiler Selection**: Dropdown to choose LaTeX compiler
- **Status Display**: Shows compiler availability and compilation status

## Usage

### Opening LaTeX Editor
1. Go to **Tools** → **Edit LaTeX** in the main editor
2. A new LaTeX tab will open with full functionality

### Basic LaTeX Editing
1. Write LaTeX code in the main editor area
2. Use toolbar buttons for common formatting
3. Press **F5** to compile or click the **▶ Run** button
4. View output and errors in the output panel

### Layout Customization
- **View** → **Layout** → **Vertical/Horizontal**: Change panel arrangement
- **View** → **Number Line**: Toggle line numbers
- **View** → **Minimap**: Toggle code overview
- **View** → **Output Panel**: Toggle compilation output

### Search & Navigation
- Use the search bar at the bottom to find text
- Navigate between search results with ↑/↓ buttons
- Search results are highlighted and counted

## File Structure
```
Latex_edit/
├── __init__.py              # Package initialization
├── latex_env.py             # Main LaTeX editor environment
├── latex_highlighter.py     # Syntax highlighting for LaTeX
├── word_suggester.py        # Auto-completion suggestions
├── test_sample.tex          # Sample LaTeX file for testing
└── README.md               # This documentation
```

## Integration Points

### Signals
- `file_saved(str)`: Emitted when a file is saved
- `file_opened(str)`: Emitted when a file is opened
- `content_changed()`: Emitted when content is modified

### Methods
- `get_editor()`: Returns the QTextEdit widget
- `get_file_path()`: Returns current file path
- `set_file_path(path)`: Sets the file path
- `get_content()`: Returns editor content
- `set_content(content)`: Sets editor content

## Requirements
- PyQt5
- LaTeX distribution (TeX Live, MiKTeX, etc.)
- At least one of: pdflatex, xelatex, or lualatex

## Troubleshooting

### No LaTeX Compiler Found
- Install a LaTeX distribution (TeX Live, MiKTeX)
- Ensure pdflatex, xelatex, or lualatex is in your PATH
- Check the status label in the control panel

### Compilation Errors
- Check the output panel for detailed error messages
- Verify LaTeX syntax in your document
- Ensure all required packages are installed

### UI Issues
- Try toggling panels on/off in the View menu
- Switch between vertical and horizontal layouts
- Restart the editor if panels become unresponsive

## Future Enhancements
- Structure view (document outline)
- Symbol panel with common LaTeX symbols
- Bibliography management
- PDF preview integration
- Spell checking
- Advanced auto-completion with context awareness 