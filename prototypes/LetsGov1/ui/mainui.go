/*
read the editor's main UI logic
This file contains the main UI logic for the editor application.
Create a simple but modern Ui text editor with the following features:
1) A menu bar with options for file operations (New, Open, Save, Save As, Close, Exit)
2) A edit menu bar with options for text manipulation (Undo, Redo, Cut, Copy, Paste, Select All)
3) A toolbar with buttons for common actions (New, Open, Save, Undo, Redo, Cut, Copy, Paste, Select All) the toolbar should be customizable
and allow the user to add or remove buttons and remove the toolbar if they want.(Add a search button that will open the search functionality)
4) A status bar that shows the current file name, cursor position, and other relevant information
5) A text area for editing the text with numberline integrated
6) make the app simple but modern looking with a clean design
*/

package ui

import (
	"fmt"
	"strings"
)

// MainUI is the main UI controller for the editor
// It manages the canvas and all UI elements
//
type MainUI struct {
	Canvas    *Canvas
	MenuBar   MenuBar
	EditBar   EditBar
	Toolbar   Toolbar
	StatusBar StatusBar
	TextArea  TextArea
	Initialized bool
}

// MenuBar represents the file operations menu
//
type MenuBar struct {
	Items []MenuItem
	Visible bool
}

// MenuItem represents a menu item
type MenuItem struct {
	Label  string
	Action string
	Key    string // Keyboard shortcut
}

// EditBar represents the edit operations menu
//
type EditBar struct {
	Items []MenuItem
	Visible bool
}

// Toolbar represents the customizable toolbar
//
type Toolbar struct {
	Buttons []ToolbarButton
	Visible bool
	Customizable bool
}

// ToolbarButton represents a toolbar button
type ToolbarButton struct {
	Label  string
	Action string
	Icon   string // Simple text icon
}

// StatusBar shows file name, cursor position, etc.
//
type StatusBar struct {
	FileName     string
	CursorLine   int
	CursorColumn int
	FileSize     int
	Modified     bool
	Visible      bool
}

// TextArea is the main text editing area, with numberline integrated
//
type TextArea struct {
	Content      string
	CursorLine   int
	CursorColumn int
	ScrollOffset int
	ShowNumbers  bool
	Visible      bool
}

// Initialize sets up the main UI with all components
func (ui *MainUI) Initialize() {
	if ui.Canvas == nil {
		ui.Canvas = NewCanvas(120, 40) // Default terminal size
	}
	
	// Initialize MenuBar
	ui.MenuBar = MenuBar{
		Items: []MenuItem{
			{Label: "New", Action: "new_file", Key: "Ctrl+N"},
			{Label: "Open", Action: "open_file", Key: "Ctrl+O"},
			{Label: "Save", Action: "save_file", Key: "Ctrl+S"},
			{Label: "Save As", Action: "save_as", Key: "Ctrl+Shift+S"},
			{Label: "Close", Action: "close_file", Key: "Ctrl+W"},
			{Label: "Exit", Action: "quit", Key: "Ctrl+Q"},
		},
		Visible: true,
	}
	
	// Initialize EditBar
	ui.EditBar = EditBar{
		Items: []MenuItem{
			{Label: "Undo", Action: "undo", Key: "Ctrl+Z"},
			{Label: "Redo", Action: "redo", Key: "Ctrl+Y"},
			{Label: "Cut", Action: "cut", Key: "Ctrl+X"},
			{Label: "Copy", Action: "copy", Key: "Ctrl+C"},
			{Label: "Paste", Action: "paste", Key: "Ctrl+V"},
			{Label: "Select All", Action: "select_all", Key: "Ctrl+A"},
		},
		Visible: true,
	}
	
	// Initialize Toolbar
	ui.Toolbar = Toolbar{
		Buttons: []ToolbarButton{
			{Label: "New", Action: "new_file", Icon: "[+]"},
			{Label: "Open", Action: "open_file", Icon: "[O]"},
			{Label: "Save", Action: "save_file", Icon: "[S]"},
			{Label: "Undo", Action: "undo", Icon: "[U]"},
			{Label: "Redo", Action: "redo", Icon: "[R]"},
			{Label: "Search", Action: "search", Icon: "[?]"},
		},
		Visible: true,
		Customizable: true,
	}
	
	// Initialize StatusBar
	ui.StatusBar = StatusBar{
		FileName:     "untitled",
		CursorLine:   1,
		CursorColumn: 1,
		FileSize:     0,
		Modified:     false,
		Visible:      true,
	}
	
	// Initialize TextArea
	ui.TextArea = TextArea{
		Content:      "",
		CursorLine:   1,
		CursorColumn: 1,
		ScrollOffset: 0,
		ShowNumbers:  true,
		Visible:      true,
	}
	
	// Add windows to canvas
	ui.addUIWindows()
	ui.Initialized = true
	
	fmt.Println("Main UI initialized with modern, clean design")
}

// addUIWindows adds all UI components as windows to the canvas
func (ui *MainUI) addUIWindows() {
	// Add menu bar window
	if ui.MenuBar.Visible {
		menuContent := ui.renderMenuBar()
		ui.Canvas.AddWindow(Window{
			Title:      "Menu Bar",
			X:          0,
			Y:          0,
			Width:      ui.Canvas.Width,
			Height:     3,
			Content:    menuContent,
			Visible:    true,
			Resizable:  false,
			WindowType: "menu",
		})
	}
	
	// Add edit bar window (buffers menu as requested)
	if ui.EditBar.Visible {
		editContent := ui.renderEditBar()
		ui.Canvas.AddWindow(Window{
			Title:      "Buffers",
			X:          0,
			Y:          3,
			Width:      ui.Canvas.Width,
			Height:     3,
			Content:    editContent,
			Visible:    true,
			Resizable:  false,
			WindowType: "menu",
		})
	}
	
	// Add toolbar window
	if ui.Toolbar.Visible {
		toolbarContent := ui.renderToolbar()
		ui.Canvas.AddWindow(Window{
			Title:      "Toolbar",
			X:          0,
			Y:          6,
			Width:      ui.Canvas.Width,
			Height:     3,
			Content:    toolbarContent,
			Visible:    true,
			Resizable:  false,
			WindowType: "toolbar",
		})
	}
	
	// Add text area window (main editor)
	if ui.TextArea.Visible {
		textContent := ui.renderTextArea()
		ui.Canvas.AddWindow(Window{
			Title:      "Editor",
			X:          0,
			Y:          9,
			Width:      ui.Canvas.Width,
			Height:     ui.Canvas.Height - 12, // Leave space for status bar
			Content:    textContent,
			Visible:    true,
			Resizable:  true,
			WindowType: "editor",
		})
	}
	
	// Add status bar window
	if ui.StatusBar.Visible {
		statusContent := ui.renderStatusBar()
		ui.Canvas.AddWindow(Window{
			Title:      "Status Bar",
			X:          0,
			Y:          ui.Canvas.Height - 3,
			Width:      ui.Canvas.Width,
			Height:     3,
			Content:    statusContent,
			Visible:    true,
			Resizable:  false,
			WindowType: "status",
		})
	}
}

// renderMenuBar creates the menu bar content
func (ui *MainUI) renderMenuBar() string {
	var content strings.Builder
	content.WriteString("File: ")
	
	for i, item := range ui.MenuBar.Items {
		if i > 0 {
			content.WriteString(" | ")
		}
		content.WriteString(fmt.Sprintf("%s (%s)", item.Label, item.Key))
	}
	
	return content.String()
}

// renderEditBar creates the edit bar content (buffers menu)
func (ui *MainUI) renderEditBar() string {
	var content strings.Builder
	content.WriteString("Edit: ")
	
	for i, item := range ui.EditBar.Items {
		if i > 0 {
			content.WriteString(" | ")
		}
		content.WriteString(fmt.Sprintf("%s (%s)", item.Label, item.Key))
	}
	
	return content.String()
}

// renderToolbar creates the toolbar content
func (ui *MainUI) renderToolbar() string {
	var content strings.Builder
	content.WriteString("Tools: ")
	
	for i, button := range ui.Toolbar.Buttons {
		if i > 0 {
			content.WriteString(" ")
		}
		content.WriteString(fmt.Sprintf("%s%s", button.Icon, button.Label))
	}
	
	if ui.Toolbar.Customizable {
		content.WriteString(" (Customizable)")
	}
	
	return content.String()
}

// renderTextArea creates the text area content with line numbers
func (ui *MainUI) renderTextArea() string {
	var content strings.Builder
	
	if ui.TextArea.Content == "" {
		if ui.TextArea.ShowNumbers {
			content.WriteString("1 | (empty file)")
		} else {
			content.WriteString("(empty file)")
		}
	} else {
		lines := strings.Split(ui.TextArea.Content, "\n")
		for i, line := range lines {
			lineNum := i + 1 + ui.TextArea.ScrollOffset
			if ui.TextArea.ShowNumbers {
				content.WriteString(fmt.Sprintf("%3d | %s\n", lineNum, line))
			} else {
				content.WriteString(line + "\n")
			}
		}
	}
	
	// Add cursor position indicator
	content.WriteString(fmt.Sprintf("\nCursor: Line %d, Column %d", 
		ui.TextArea.CursorLine, ui.TextArea.CursorColumn))
	
	return content.String()
}

// renderStatusBar creates the status bar content
func (ui *MainUI) renderStatusBar() string {
	modifiedIndicator := ""
	if ui.StatusBar.Modified {
		modifiedIndicator = "*"
	}
	
	return fmt.Sprintf("File: %s%s | Line: %d, Col: %d | Size: %d bytes", 
		ui.StatusBar.FileName, 
		modifiedIndicator,
		ui.StatusBar.CursorLine, 
		ui.StatusBar.CursorColumn,
		ui.StatusBar.FileSize)
}

// Render draws the entire UI using the canvas
func (ui *MainUI) Render() {
	if !ui.Initialized {
		ui.Initialize()
	}
	
	// Update window contents
	ui.updateWindowContents()
	
	// Render the canvas
	ui.Canvas.Render()
}

// updateWindowContents updates the content of all UI windows
func (ui *MainUI) updateWindowContents() {
	ui.Canvas.UpdateWindowContent("Menu Bar", ui.renderMenuBar())
	ui.Canvas.UpdateWindowContent("Buffers", ui.renderEditBar())
	ui.Canvas.UpdateWindowContent("Toolbar", ui.renderToolbar())
	ui.Canvas.UpdateWindowContent("Editor", ui.renderTextArea())
	ui.Canvas.UpdateWindowContent("Status Bar", ui.renderStatusBar())
}

// UpdateTextContent updates the text area content
func (ui *MainUI) UpdateTextContent(content string) {
	ui.TextArea.Content = content
	ui.StatusBar.FileSize = len(content)
	ui.StatusBar.Modified = true
	
	// Update line count
	lines := strings.Split(content, "\n")
	if len(lines) > 0 {
		ui.TextArea.CursorLine = len(lines)
	}
}

// UpdateFileName updates the current file name
func (ui *MainUI) UpdateFileName(fileName string) {
	ui.StatusBar.FileName = fileName
	ui.StatusBar.Modified = false
}

// UpdateCursorPosition updates cursor position
func (ui *MainUI) UpdateCursorPosition(line, column int) {
	ui.TextArea.CursorLine = line
	ui.TextArea.CursorColumn = column
	ui.StatusBar.CursorLine = line
	ui.StatusBar.CursorColumn = column
}

// ToggleLineNumbers toggles line number display
func (ui *MainUI) ToggleLineNumbers() {
	ui.TextArea.ShowNumbers = !ui.TextArea.ShowNumbers
	fmt.Printf("Line numbers: %t\n", ui.TextArea.ShowNumbers)
}

// ToggleToolbar toggles toolbar visibility
func (ui *MainUI) ToggleToolbar() {
	ui.Toolbar.Visible = !ui.Toolbar.Visible
	ui.Canvas.ToggleWindowVisibility("Toolbar")
	fmt.Printf("Toolbar visibility: %t\n", ui.Toolbar.Visible)
}

// AddToolbarButton adds a custom button to the toolbar
func (ui *MainUI) AddToolbarButton(label, action, icon string) {
	if ui.Toolbar.Customizable {
		ui.Toolbar.Buttons = append(ui.Toolbar.Buttons, ToolbarButton{
			Label:  label,
			Action: action,
			Icon:   icon,
		})
		fmt.Printf("Added toolbar button: %s\n", label)
	}
}

// RemoveToolbarButton removes a button from the toolbar
func (ui *MainUI) RemoveToolbarButton(label string) bool {
	if !ui.Toolbar.Customizable {
		return false
	}
	
	for i, button := range ui.Toolbar.Buttons {
		if button.Label == label {
			ui.Toolbar.Buttons = append(ui.Toolbar.Buttons[:i], ui.Toolbar.Buttons[i+1:]...)
			fmt.Printf("Removed toolbar button: %s\n", label)
			return true
		}
	}
	return false
}
