/*
Everything will be initiated and shown to the user through the canvas / The canvas will be
 the area were the UI will be shown and initiated however it will be very easy to support new
 UI elemets and scripts :
In canvas :
Every window will be resisable
It can support showing multiple scripts
it will be lightweight and error free (as much as we can at least)
The whole idea
The canvas will be exactly like a paint canvas
*/

package ui

import (
	"fmt"
	"strings"
)

// Canvas is the central UI area for the editor
// All UI elements are rendered here
// Supports multiple resizable windows and lightweight rendering
//
type Canvas struct {
	Windows []Window // All open windows/scripts
	Width   int      // Canvas width
	Height  int      // Canvas height
}

// Window represents a resizable UI window on the canvas
// This can be a text editor, menu, toolbar, etc.
type Window struct {
	Title    string
	X, Y     int    // Position
	Width    int    // Window width
	Height   int    // Window height
	Content  string // Window content
	Visible  bool   // Whether window is visible
	Resizable bool  // Whether window can be resized
	WindowType string // Type: "editor", "menu", "toolbar", "status", etc.
}

// NewCanvas creates a new canvas with default dimensions
func NewCanvas(width, height int) *Canvas {
	return &Canvas{
		Windows: []Window{},
		Width:   width,
		Height:  height,
	}
}

// AddWindow adds a new window to the canvas
func (c *Canvas) AddWindow(window Window) {
	window.Visible = true
	c.Windows = append(c.Windows, window)
	fmt.Printf("Added window: %s (%s)\n", window.Title, window.WindowType)
}

// RemoveWindow removes a window by title
func (c *Canvas) RemoveWindow(title string) bool {
	for i, window := range c.Windows {
		if window.Title == title {
			c.Windows = append(c.Windows[:i], c.Windows[i+1:]...)
			fmt.Printf("Removed window: %s\n", title)
			return true
		}
	}
	return false
}

// FindWindow finds a window by title
func (c *Canvas) FindWindow(title string) *Window {
	for i := range c.Windows {
		if c.Windows[i].Title == title {
			return &c.Windows[i]
		}
	}
	return nil
}

// ResizeWindow resizes a window if it's resizable
func (c *Canvas) ResizeWindow(title string, width, height int) bool {
	window := c.FindWindow(title)
	if window == nil {
		return false
	}
	
	if !window.Resizable {
		fmt.Printf("Window '%s' is not resizable\n", title)
		return false
	}
	
	// Ensure window stays within canvas bounds
	if window.X + width > c.Width {
		width = c.Width - window.X
	}
	if window.Y + height > c.Height {
		height = c.Height - window.Y
	}
	
	window.Width = width
	window.Height = height
	fmt.Printf("Resized window '%s' to %dx%d\n", title, width, height)
	return true
}

// MoveWindow moves a window to a new position
func (c *Canvas) MoveWindow(title string, x, y int) bool {
	window := c.FindWindow(title)
	if window == nil {
		return false
	}
	
	// Ensure window stays within canvas bounds
	if x < 0 {
		x = 0
	}
	if y < 0 {
		y = 0
	}
	if x + window.Width > c.Width {
		x = c.Width - window.Width
	}
	if y + window.Height > c.Height {
		y = c.Height - window.Height
	}
	
	window.X = x
	window.Y = y
	fmt.Printf("Moved window '%s' to (%d, %d)\n", title, x, y)
	return true
}

// ToggleWindowVisibility toggles a window's visibility
func (c *Canvas) ToggleWindowVisibility(title string) bool {
	window := c.FindWindow(title)
	if window == nil {
		return false
	}
	
	window.Visible = !window.Visible
	fmt.Printf("Window '%s' visibility: %t\n", title, window.Visible)
	return true
}

// UpdateWindowContent updates the content of a window
func (c *Canvas) UpdateWindowContent(title, content string) bool {
	window := c.FindWindow(title)
	if window == nil {
		return false
	}
	
	window.Content = content
	return true
}

// Render draws all windows/scripts on the canvas
func (c *Canvas) Render() {
	fmt.Printf("\n=== Canvas (%dx%d) ===\n", c.Width, c.Height)
	
	if len(c.Windows) == 0 {
		fmt.Println("No windows open")
		return
	}
	
	// Sort windows by type for consistent rendering order
	menuWindows := []Window{}
	toolbarWindows := []Window{}
	editorWindows := []Window{}
	statusWindows := []Window{}
	otherWindows := []Window{}
	
	for _, window := range c.Windows {
		if !window.Visible {
			continue
		}
		
		switch window.WindowType {
		case "menu":
			menuWindows = append(menuWindows, window)
		case "toolbar":
			toolbarWindows = append(toolbarWindows, window)
		case "editor":
			editorWindows = append(editorWindows, window)
		case "status":
			statusWindows = append(statusWindows, window)
		default:
			otherWindows = append(otherWindows, window)
		}
	}
	
	// Render in order: menu, toolbar, editor, other, status
	allWindows := append(menuWindows, toolbarWindows...)
	allWindows = append(allWindows, editorWindows...)
	allWindows = append(allWindows, otherWindows...)
	allWindows = append(allWindows, statusWindows...)
	
	for _, window := range allWindows {
		c.renderWindow(window)
	}
}

// renderWindow renders a single window
func (c *Canvas) renderWindow(window Window) {
	fmt.Printf("\n[%s] %s at (%d,%d) %dx%d\n", 
		strings.ToUpper(window.WindowType), 
		window.Title, 
		window.X, window.Y, 
		window.Width, window.Height)
	
	if window.Content != "" {
		// Simple content rendering - in a real implementation this would be more sophisticated
		lines := strings.Split(window.Content, "\n")
		maxLines := window.Height - 2 // Leave space for borders
		if maxLines < 1 {
			maxLines = 1
		}
		
		for i, line := range lines {
			if i >= maxLines {
				fmt.Println("  ...")
				break
			}
			
			// Truncate line if too long
			maxWidth := window.Width - 4 // Leave space for borders
			if maxWidth < 1 {
				maxWidth = 10 // Minimum width to prevent negative slice bounds
			}
			
			if len(line) > maxWidth {
				if maxWidth > 3 {
					line = line[:maxWidth-3] + "..."
				} else {
					line = "..."
				}
			}
			
			fmt.Printf("  %s\n", line)
		}
	} else {
		fmt.Println("  (empty)")
	}
}

// GetWindowCount returns the number of windows
func (c *Canvas) GetWindowCount() int {
	return len(c.Windows)
}

// GetVisibleWindowCount returns the number of visible windows
func (c *Canvas) GetVisibleWindowCount() int {
	count := 0
	for _, window := range c.Windows {
		if window.Visible {
			count++
		}
	}
	return count
}

// ListWindows lists all windows with their properties
func (c *Canvas) ListWindows() {
	fmt.Printf("\n=== Canvas Windows (%d total) ===\n", len(c.Windows))
	for i, window := range c.Windows {
		visibility := "visible"
		if !window.Visible {
			visibility = "hidden"
		}
		resizable := "resizable"
		if !window.Resizable {
			resizable = "fixed"
		}
		
		fmt.Printf("%d. %s (%s) - %s, %s - (%d,%d) %dx%d\n", 
			i+1, window.Title, window.WindowType, 
			visibility, resizable,
			window.X, window.Y, window.Width, window.Height)
	}
	fmt.Println()
}
