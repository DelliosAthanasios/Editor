/* Here add the main logic of the application
let me list it for you:
New File = Creates a new file
Open file = Opens an existing file
Save File = Saves the current file
Duplicate File = Duplicates the current file
Save all = Saves all open files
Close File = Closes the current file
Edit File = Edits the current file
Delete File = Deletes the current file
*/
/*
Then we have text manipulation functions:
 undo = Undoes the last action
 redo = Redoes the last undone action
 Select All = Selects all text in the current file
 Go to Start of a line = Moves the cursor to the start of the current line
 Go to End of a line = Moves the cursor to the end of the current line
 Go to Start of a file = Moves the cursor to the start of the file
 Go to End of a file = Moves the cursor to the end of the file
 go to Next word = Moves the cursor to the next word
 go to Previous word = Moves the cursor to the previous word
 delete word = Deletes the word at the cursor position
 delete line = Deletes the current line
 go forward one character = Moves the cursor one character forward
 go backward one character = Moves the cursor one character backward
 go to next line = Moves the cursor to the next line
 go to previous line = Moves the cursor to the previous line
*/
/*
 we will continue with more text manipulation functions in the future
*/

package logic

import (
	"fmt"
	"io/ioutil"
	"os"
)

// EditManager handles all file and text manipulation actions
//
type EditManager struct {
	UndoStack []string // Stack for undo operations
	RedoStack []string // Stack for redo operations
	CurrentFile string // Currently open file path
}

// File operations
func (em *EditManager) NewFile() {
	em.CurrentFile = ""
	em.UndoStack = []string{}
	em.RedoStack = []string{}
	fmt.Println("New file created")
}

func (em *EditManager) OpenFile(filename string) {
	if filename == "" {
		fmt.Println("No filename provided")
		return
	}
	
	content, err := ioutil.ReadFile(filename)
	if err != nil {
		fmt.Printf("Error opening file %s: %v\n", filename, err)
		return
	}
	
	em.CurrentFile = filename
	em.UndoStack = []string{string(content)}
	em.RedoStack = []string{}
	fmt.Printf("File opened: %s\n", filename)
}

func (em *EditManager) SaveFile() {
	if em.CurrentFile == "" {
		fmt.Println("No file to save. Use SaveAs instead.")
		return
	}
	
	if len(em.UndoStack) == 0 {
		fmt.Println("No content to save")
		return
	}
	
	content := em.UndoStack[len(em.UndoStack)-1]
	err := ioutil.WriteFile(em.CurrentFile, []byte(content), 0644)
	if err != nil {
		fmt.Printf("Error saving file: %v\n", err)
		return
	}
	
	fmt.Printf("File saved: %s\n", em.CurrentFile)
}

func (em *EditManager) DuplicateFile() {
	if em.CurrentFile == "" {
		fmt.Println("No file to duplicate")
		return
	}
	
	newName := em.CurrentFile + ".copy"
	content, err := ioutil.ReadFile(em.CurrentFile)
	if err != nil {
		fmt.Printf("Error reading file for duplication: %v\n", err)
		return
	}
	
	err = ioutil.WriteFile(newName, content, 0644)
	if err != nil {
		fmt.Printf("Error creating duplicate: %v\n", err)
		return
	}
	
	fmt.Printf("File duplicated as: %s\n", newName)
}

func (em *EditManager) SaveAll() {
	// For now, just save the current file
	em.SaveFile()
	fmt.Println("All files saved")
}

func (em *EditManager) CloseFile() {
	em.CurrentFile = ""
	em.UndoStack = []string{}
	em.RedoStack = []string{}
	fmt.Println("File closed")
}

func (em *EditManager) EditFile() {
	if em.CurrentFile != "" {
		fmt.Printf("Editing file: %s\n", em.CurrentFile)
	} else {
		fmt.Println("No file open for editing")
	}
}

func (em *EditManager) DeleteFile() {
	if em.CurrentFile == "" {
		fmt.Println("No file to delete")
		return
	}
	
	err := os.Remove(em.CurrentFile)
	if err != nil {
		fmt.Printf("Error deleting file: %v\n", err)
		return
	}
	
	fmt.Printf("File deleted: %s\n", em.CurrentFile)
	em.CloseFile()
}

// Text manipulation
func (em *EditManager) Undo() {
	if len(em.UndoStack) <= 1 {
		fmt.Println("Nothing to undo")
		return
	}
	
	// Move current state to redo stack
	current := em.UndoStack[len(em.UndoStack)-1]
	em.RedoStack = append(em.RedoStack, current)
	
	// Remove current state from undo stack
	em.UndoStack = em.UndoStack[:len(em.UndoStack)-1]
	
	fmt.Println("Undo performed")
}

func (em *EditManager) Redo() {
	if len(em.RedoStack) == 0 {
		fmt.Println("Nothing to redo")
		return
	}
	
	// Move state from redo to undo stack
	state := em.RedoStack[len(em.RedoStack)-1]
	em.RedoStack = em.RedoStack[:len(em.RedoStack)-1]
	em.UndoStack = append(em.UndoStack, state)
	
	fmt.Println("Redo performed")
}

func (em *EditManager) SelectAll() {
	fmt.Println("All text selected")
}

func (em *EditManager) GoToStartOfLine() {
	fmt.Println("Cursor moved to start of line")
}

func (em *EditManager) GoToEndOfLine() {
	fmt.Println("Cursor moved to end of line")
}

func (em *EditManager) GoToStartOfFile() {
	fmt.Println("Cursor moved to start of file")
}

func (em *EditManager) GoToEndOfFile() {
	fmt.Println("Cursor moved to end of file")
}

func (em *EditManager) GoToNextWord() {
	fmt.Println("Cursor moved to next word")
}

func (em *EditManager) GoToPreviousWord() {
	fmt.Println("Cursor moved to previous word")
}

func (em *EditManager) DeleteWord() {
	fmt.Println("Word deleted")
}

func (em *EditManager) DeleteLine() {
	fmt.Println("Line deleted")
}

func (em *EditManager) GoForwardChar() {
	fmt.Println("Cursor moved forward one character")
}

func (em *EditManager) GoBackwardChar() {
	fmt.Println("Cursor moved backward one character")
}

func (em *EditManager) GoToNextLine() {
	fmt.Println("Cursor moved to next line")
}

func (em *EditManager) GoToPreviousLine() {
	fmt.Println("Cursor moved to previous line")
}
