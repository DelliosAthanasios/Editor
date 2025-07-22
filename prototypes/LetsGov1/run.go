// Main entry point and central state management for the editor
// This file follows all principles from rulestofollow.md and user instructions in each module

package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"letsgo-editor/featu"
	"letsgo-editor/keybinds"
	"letsgo-editor/logic"
	"letsgo-editor/ui"
)

// EditorState holds the entire application state
// This struct is the single source of truth for the editor
// It will be expanded as features are implemented
// All UI and logic will reference this state
//
type EditorState struct {
	BuffersManager *logic.BuffersManager // Buffer management
	EditManager    *logic.EditManager    // Edit operations
	SearchManager  *logic.SearchManager  // Search/replace
	KeybindManager *keybinds.KeybindManager // Keybindings
	FontEdit       *featu.FontEdit       // Font management
	NumberLine     *featu.NumberLine     // Line numbers
	MainUI         *ui.MainUI            // Main UI
	Theme          *ui.Theme             // Current theme
	Running        bool                  // Application state
}

// Initialize creates a new editor state with all components
func (state *EditorState) Initialize() {
	state.BuffersManager = &logic.BuffersManager{
		Buffers:      []logic.Buffer{},
		ActiveBuffer: 0,
	}
	state.EditManager = &logic.EditManager{}
	state.SearchManager = &logic.SearchManager{
		CaseSensitive: false,
		UseRegex:      false,
		Results:       []int{},
		CurrentIndex:  0,
	}
	state.KeybindManager = &keybinds.KeybindManager{
		Bindings: []keybinds.Keybinding{},
	}
	state.FontEdit = &featu.FontEdit{FontSize: 14}
	state.NumberLine = &featu.NumberLine{
		TotalLines:   1,
		CurrentLine:  1,
		ScrollOffset: 0,
	}
	
	// Initialize theme
	state.Theme = &ui.Theme{
		BackgroundColor: "#1e1e1e",
		ForegroundColor: "#d4d4d4",
		AccentColor:     "#007acc",
		MenuBarColor:    "#2d2d30",
		StatusBarColor:  "#007acc",
		TextAreaColor:   "#1e1e1e",
		NumberLineColor: "#858585",
	}
	
	// Initialize UI with canvas
	canvas := &ui.Canvas{Windows: []ui.Window{}, Width: 120, Height: 40}
	state.MainUI = &ui.MainUI{
		Canvas:    canvas,
		MenuBar:   ui.MenuBar{},
		EditBar:   ui.EditBar{},
		Toolbar:   ui.Toolbar{},
		StatusBar: ui.StatusBar{},
		TextArea:  ui.TextArea{},
	}
	
	state.Running = true
	
	// Load default keybindings
	state.loadDefaultKeybindings()
}

// loadDefaultKeybindings sets up the default keyboard shortcuts
func (state *EditorState) loadDefaultKeybindings() {
	defaultBindings := []keybinds.Keybinding{
		{Action: "new_file", Key: "Ctrl+N"},
		{Action: "open_file", Key: "Ctrl+O"},
		{Action: "save_file", Key: "Ctrl+S"},
		{Action: "save_all", Key: "Ctrl+Shift+S"},
		{Action: "close_file", Key: "Ctrl+W"},
		{Action: "quit", Key: "Ctrl+Q"},
		{Action: "undo", Key: "Ctrl+Z"},
		{Action: "redo", Key: "Ctrl+Y"},
		{Action: "cut", Key: "Ctrl+X"},
		{Action: "copy", Key: "Ctrl+C"},
		{Action: "paste", Key: "Ctrl+V"},
		{Action: "select_all", Key: "Ctrl+A"},
		{Action: "search", Key: "Ctrl+F"},
		{Action: "replace", Key: "Ctrl+H"},
		{Action: "font_increase", Key: "Ctrl++"},
		{Action: "font_decrease", Key: "Ctrl+-"},
		{Action: "go_to_line_start", Key: "Home"},
		{Action: "go_to_line_end", Key: "End"},
		{Action: "go_to_file_start", Key: "Ctrl+Home"},
		{Action: "go_to_file_end", Key: "Ctrl+End"},
		{Action: "next_word", Key: "Ctrl+Right"},
		{Action: "prev_word", Key: "Ctrl+Left"},
		{Action: "delete_word", Key: "Ctrl+Delete"},
		{Action: "delete_line", Key: "Ctrl+Shift+K"},
		{Action: "next_line", Key: "Down"},
		{Action: "prev_line", Key: "Up"},
		{Action: "next_char", Key: "Right"},
		{Action: "prev_char", Key: "Left"},
	}
	
	state.KeybindManager.Bindings = defaultBindings
}

// HandleInput processes user input and executes corresponding actions
func (state *EditorState) HandleInput(input string) {
	input = strings.TrimSpace(input)
	
	// Handle special commands
	switch input {
	case "quit", "exit", "q":
		state.Running = false
		return
	case "help", "h":
		state.showHelp()
		return
	case "new":
		state.EditManager.NewFile()
		fmt.Println("New file created")
		return
	case "save":
		state.EditManager.SaveFile()
		fmt.Println("File saved")
		return
	case "search":
		fmt.Print("Enter search term: ")
		reader := bufio.NewReader(os.Stdin)
		term, _ := reader.ReadString('\n')
		term = strings.TrimSpace(term)
		if term != "" {
			state.SearchManager.Search("", term) // Placeholder text
			fmt.Printf("Searching for: %s\n", term)
		}
		return
	case "font+":
		state.FontEdit.Increase()
		fmt.Printf("Font size increased to: %d\n", state.FontEdit.FontSize)
		return
	case "font-":
		state.FontEdit.Decrease()
		fmt.Printf("Font size decreased to: %d\n", state.FontEdit.FontSize)
		return
	case "theme":
		fmt.Printf("Current theme: Background=%s, Foreground=%s\n", 
			state.Theme.BackgroundColor, state.Theme.ForegroundColor)
		return
	case "status":
		state.showStatus()
		return
	}
	
	// If no special command matched, treat as regular text input
	fmt.Printf("Input received: %s\n", input)
}

// showHelp displays available commands
func (state *EditorState) showHelp() {
	fmt.Println("\n=== LetsGo Editor Help ===")
	fmt.Println("Commands:")
	fmt.Println("  help, h     - Show this help")
	fmt.Println("  new         - Create new file")
	fmt.Println("  save        - Save current file")
	fmt.Println("  search      - Search in file")
	fmt.Println("  font+       - Increase font size")
	fmt.Println("  font-       - Decrease font size")
	fmt.Println("  theme       - Show current theme")
	fmt.Println("  status      - Show editor status")
	fmt.Println("  quit, exit, q - Exit editor")
	fmt.Println("\nKeybindings:")
	for _, binding := range state.KeybindManager.Bindings {
		fmt.Printf("  %-20s - %s\n", binding.Key, binding.Action)
	}
	fmt.Println()
}

// showStatus displays current editor status
func (state *EditorState) showStatus() {
	fmt.Println("\n=== Editor Status ===")
	fmt.Printf("Open buffers: %d\n", len(state.BuffersManager.Buffers))
	fmt.Printf("Active buffer: %d\n", state.BuffersManager.ActiveBuffer)
	fmt.Printf("Font size: %d\n", state.FontEdit.FontSize)
	fmt.Printf("Current line: %d\n", state.NumberLine.CurrentLine)
	fmt.Printf("Total lines: %d\n", state.NumberLine.TotalLines)
	fmt.Printf("Search case sensitive: %t\n", state.SearchManager.CaseSensitive)
	fmt.Printf("Search regex mode: %t\n", state.SearchManager.UseRegex)
	fmt.Println()
}

// Render updates the display
func (state *EditorState) Render() {
	// Clear screen (simple implementation)
	fmt.Print("\033[2J\033[H")
	
	// Render UI
	fmt.Println("=== LetsGo Editor ===")
	fmt.Printf("Font Size: %d | Line: %d/%d | Buffers: %d\n", 
		state.FontEdit.FontSize, 
		state.NumberLine.CurrentLine, 
		state.NumberLine.TotalLines,
		len(state.BuffersManager.Buffers))
	fmt.Println("Type 'help' for commands, 'quit' to exit")
	fmt.Println("---")
	
	// Render main UI components
	state.MainUI.Render()
}

// main initializes the editor and enters the main event loop
func main() {
	// Initialize the editor state
	var state EditorState
	state.Initialize()
	
	fmt.Println("LetsGo Editor - A modular, keyboard-driven text editor")
	fmt.Println("Following principles: keyboard navigation, modularity, simplicity")
	fmt.Println("Type 'help' for available commands")
	
	// Create input reader
	reader := bufio.NewReader(os.Stdin)
	
	// Main event loop - completely keyboard driven
	for state.Running {
		// Render the current state
		state.Render()
		
		// Get user input
		fmt.Print("> ")
		input, err := reader.ReadString('\n')
		if err != nil {
			fmt.Printf("Error reading input: %v\n", err)
			continue
		}
		
		// Handle the input
		state.HandleInput(input)
	}
	
	fmt.Println("LetsGo Editor closed. Goodbye!")
}
