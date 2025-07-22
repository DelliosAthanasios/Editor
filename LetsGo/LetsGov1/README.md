# LetsGo Editor

A modular, keyboard-driven text editor built in Go, following principles of simplicity, modularity, and complete keyboard navigation.

## Features

### Core Principles
- **Completely keyboard navigatable** - Every action can be performed via keyboard
- **Modular design** - Easy to extend and customize
- **Lightweight and error-free** - Minimal resource usage with robust error handling
- **Canvas-based UI** - All UI elements rendered on a flexible canvas system
- **Beginner-friendly** - Straightforward interface, unlike complex editors like Emacs

### UI Components
- **Menu Bar** - File operations (New, Open, Save, Save As, Close, Exit)
- **Edit Bar (Buffers)** - Text manipulation (Undo, Redo, Cut, Copy, Paste, Select All)
- **Customizable Toolbar** - Quick access buttons with icons
- **Text Area** - Main editing area with integrated line numbers
- **Status Bar** - Shows file name, cursor position, file size, and modification status

### Text Editing Features
- File operations: New, Open, Save, Duplicate, Save All, Close, Delete
- Text manipulation: Undo/Redo, Cut/Copy/Paste, Select All
- Navigation: Line start/end, file start/end, word navigation, character navigation
- Search and replace with regex support and case sensitivity options
- Font size adjustment
- Line number display (toggleable)

### Modular Architecture
- **`ui/`** - Canvas system, main UI, themes
- **`logic/`** - Buffer management, edit operations, search functionality
- **`keybinds/`** - Comprehensive keybinding system with customization
- **`featu/`** - Font editing and number line features

## Installation and Usage

### Prerequisites
- Go 1.18 or later

### Building
```bash
cd LetsGo
go mod tidy
go build -o letsgo-editor .
```

### Running
```bash
./letsgo-editor
```

## Commands

### Basic Commands
- `help`, `h` - Show help and keybindings
- `new` - Create new file
- `save` - Save current file
- `search` - Search in file
- `font+` - Increase font size
- `font-` - Decrease font size
- `theme` - Show current theme
- `status` - Show editor status
- `quit`, `exit`, `q` - Exit editor

### Default Keybindings

#### File Operations
- `Ctrl+N` - New file
- `Ctrl+O` - Open file
- `Ctrl+S` - Save file
- `Ctrl+Shift+S` - Save all files
- `Ctrl+W` - Close file
- `Ctrl+Q` - Quit editor

#### Edit Operations
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+X` - Cut
- `Ctrl+C` - Copy
- `Ctrl+V` - Paste
- `Ctrl+A` - Select all

#### Navigation
- `Home` - Go to start of line
- `End` - Go to end of line
- `Ctrl+Home` - Go to start of file
- `Ctrl+End` - Go to end of file
- `Ctrl+Right` - Next word
- `Ctrl+Left` - Previous word
- `Up/Down/Left/Right` - Character and line navigation

#### Search and Replace
- `Ctrl+F` - Search
- `Ctrl+H` - Replace

#### Font and Display
- `Ctrl++` - Increase font size
- `Ctrl+-` - Decrease font size

#### Text Manipulation
- `Ctrl+Delete` - Delete word
- `Ctrl+Shift+K` - Delete line

## Architecture

### Canvas System
The editor uses a canvas-based UI system where all components are rendered as windows on a canvas. This allows for:
- Resizable windows
- Multiple script/application support
- Lightweight rendering
- Easy extension with new UI elements

### Modular Design
Each component is designed as a separate module:
- **BuffersManager** - Manages open files/tabs
- **EditManager** - Handles file and text operations
- **SearchManager** - Provides search and replace functionality
- **KeybindManager** - Manages keyboard shortcuts
- **FontEdit** - Controls font sizing
- **NumberLine** - Displays line numbers
- **Theme** - Manages color schemes

### Extensibility
The modular architecture makes it easy to:
- Add new keybindings
- Implement new features
- Customize the UI
- Add new themes
- Extend functionality

## Customization

### Keybindings
Keybindings can be customized by modifying the `KeybindManager`. The system supports:
- Loading/saving keybindings from files
- Adding custom keybindings
- Removing existing keybindings
- Validation to prevent conflicts

### Themes
The theme system allows customization of:
- Background colors
- Foreground colors
- Accent colors
- Menu bar colors
- Status bar colors
- Text area colors
- Number line colors

### Toolbar
The toolbar is fully customizable:
- Add/remove buttons
- Custom icons
- Custom actions
- Toggle visibility

## Future Expansion

The editor is designed as a strong foundation for future expansions:
- Split-screen functionality
- Multiple editor instances
- Dedicated Excel-style applications
- Plugin system
- Advanced text editing features
- Real-time collaboration
- Version control integration

## Development

### Project Structure
```
LetsGo/
├── run.go              # Main entry point
├── go.mod              # Go module file
├── README.md           # This file
├── rulestofollow.md    # Design principles
├── todo.md             # Development progress
├── featu/              # Feature modules
│   ├── fondedit.go     # Font editing
│   └── numberline.go   # Line numbers
├── keybinds/           # Keybinding system
│   └── mainkeys.go     # Keybinding management
├── logic/              # Core logic
│   ├── buffers.go      # Buffer management
│   ├── editlogic.go    # Edit operations
│   └── searching.go    # Search functionality
└── ui/                 # User interface
    ├── canvas.go       # Canvas system
    ├── mainui.go       # Main UI components
    └── themes.go       # Theme management
```

### Contributing
The modular design makes it easy to contribute:
1. Each module is self-contained
2. Clear separation of concerns
3. Comprehensive keybinding system
4. Extensible architecture

## License

This project follows the principles of modularity, simplicity, and keyboard-driven design to create a foundation for advanced text editing applications.

