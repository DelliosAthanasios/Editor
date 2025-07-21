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
	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"
)

// MainUI is the main UI controller for the editor
// It manages the canvas and all UI elements
//
type MainUI struct {
	App       fyne.App
	Window    fyne.Window
	MenuBar   *fyne.MainMenu
	Toolbar   *widget.Toolbar
	StatusBar *widget.Label
	TextArea  *widget.Entry
}

// NewMainUI creates and initializes the main UI
func NewMainUI() *MainUI {
	a := app.New()
	w := a.NewWindow("LetsGo Editor")

	// Menu bar
	fileMenu := fyne.NewMenu("File",
		fyne.NewMenuItem("New", nil),
		fyne.NewMenuItem("Open", nil),
		fyne.NewMenuItem("Save", nil),
		fyne.NewMenuItem("Save As", nil),
		fyne.NewMenuItem("Close", nil),
		fyne.NewMenuItemSeparator(),
		fyne.NewMenuItem("Exit", func() { a.Quit() }),
	)
	editMenu := fyne.NewMenu("Edit",
		fyne.NewMenuItem("Undo", nil),
		fyne.NewMenuItem("Redo", nil),
		fyne.NewMenuItemSeparator(),
		fyne.NewMenuItem("Cut", nil),
		fyne.NewMenuItem("Copy", nil),
		fyne.NewMenuItem("Paste", nil),
		fyne.NewMenuItem("Select All", nil),
	)
	mainMenu := fyne.NewMainMenu(fileMenu, editMenu)
	w.SetMainMenu(mainMenu)

	// Toolbar
	toolbar := widget.NewToolbar(
		widget.NewToolbarAction(theme.DocumentCreateIcon(), func() {}),
		widget.NewToolbarAction(theme.FolderOpenIcon(), func() {}),
		widget.NewToolbarAction(theme.DocumentSaveIcon(), func() {}),
		widget.NewToolbarSeparator(),
		widget.NewToolbarAction(theme.ContentUndoIcon(), func() {}),
		widget.NewToolbarAction(theme.ContentRedoIcon(), func() {}),
		widget.NewToolbarSeparator(),
		widget.NewToolbarAction(theme.ContentCutIcon(), func() {}),
		widget.NewToolbarAction(theme.ContentCopyIcon(), func() {}),
		widget.NewToolbarAction(theme.ContentPasteIcon(), func() {}),
		widget.NewToolbarSeparator(),
		widget.NewToolbarAction(theme.SearchIcon(), func() {}),
	)

	// Status bar
	statusBar := widget.NewLabel("Ready | Line: 1, Col: 1")

	// Text area
	textArea := widget.NewMultiLineEntry()
	textArea.SetPlaceHolder("Start typing...")

	// Layout
	content := container.NewBorder(
		container.NewVBox(toolbar),   // top
		nil,                          // right
		nil,                          // left
		container.NewVBox(statusBar), // bottom
		textArea,                     // center
	)

	w.SetContent(content)
	w.Resize(fyne.NewSize(800, 600))

	return &MainUI{
		App:       a,
		Window:    w,
		MenuBar:   mainMenu,
		Toolbar:   toolbar,
		StatusBar: statusBar,
		TextArea:  textArea,
	}
}

// Run starts the main UI event loop
func (ui *MainUI) Run() {
	ui.Window.ShowAndRun()
}
