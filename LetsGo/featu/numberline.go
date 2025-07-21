/* a number line style bar which will be the same as for example in vscode
   it will be used to show the line numbers of the text area
   and it will be integrated with the text area
   so when the user scrolls the text area the number line will scroll too
   and it will be used to show the current line number of the cursor position
*/

package featu

// NumberLine displays line numbers for the text area
// It syncs with the text area and scrolls together
//
type NumberLine struct {
	TotalLines   int
	CurrentLine  int // Cursor position
	ScrollOffset int
}

// Render draws the number line (placeholder)
func (nl *NumberLine) Render() {
	// Placeholder: Render line numbers from ScrollOffset to ScrollOffset+visible lines
	// Highlight CurrentLine
}
