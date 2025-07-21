/* a simple way to change the font size of the editor
 */

package featu

// FontEdit manages the font size of the editor
//
type FontEdit struct {
	FontSize int
}

// Increase increases the font size
func (fe *FontEdit) Increase() {
	fe.FontSize++
}

// Decrease decreases the font size
func (fe *FontEdit) Decrease() {
	if fe.FontSize > 1 {
		fe.FontSize--
	}
}
