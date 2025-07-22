/* every color code from every ui element will be stored here
so it will be easer to change the color scheme of the editor
and add a theme managfer in the future */

package ui

// Theme holds all color codes for UI elements
// This makes it easy to change the color scheme and add a theme manager
//
type Theme struct {
	BackgroundColor string
	ForegroundColor string
	AccentColor     string
	MenuBarColor    string
	StatusBarColor  string
	TextAreaColor   string
	NumberLineColor string
	// Add more as needed
}

// ThemeManager will manage switching and loading themes (future)
type ThemeManager struct {
	Current Theme
	// Placeholder for theme management logic
}
