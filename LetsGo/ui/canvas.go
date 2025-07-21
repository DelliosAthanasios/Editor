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

// Canvas is the central UI area for the editor
// All UI elements are rendered here
// Supports multiple resizable windows and lightweight rendering
//
type Canvas struct {
	Windows []Window // All open windows/scripts
}

// Window represents a resizable UI window on the canvas
// This can be a text editor, menu, toolbar, etc.
type Window struct {
	Title   string
	X, Y    int // Position
	Width   int
	Height  int
	Content string // Placeholder for window content
}

// Render draws all windows/scripts on the canvas
func (c *Canvas) Render() {
	// Placeholder: Render all windows
	for _, win := range c.Windows {
		// In a real implementation, draw the window at (win.X, win.Y) with size (win.Width, win.Height)
		// and render win.Content
		// For now, just print window titles
		println("Window:", win.Title)
	}
}
