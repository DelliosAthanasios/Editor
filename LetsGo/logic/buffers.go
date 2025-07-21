/* Here we have the handling of the tabs and the splitscreen (future feature)
we will implement a tab system that allows users to open multiple files in the same window
and switch between them easily.
The tabs will be displayed like emacs so it will create a menu bar were all the open files will be shown
and all the splitscreens instances will be shown in the mainui.go add menu bar named buffers */

package logic

// Buffer represents an open file/tab
//
type Buffer struct {
	Name    string
	Content string
	Cursor  int
}

// BuffersManager manages all open buffers/tabs
//
type BuffersManager struct {
	Buffers      []Buffer
	ActiveBuffer int // Index of the currently active buffer
}

// AddBuffer adds a new buffer/tab
func (bm *BuffersManager) AddBuffer(buf Buffer) {
	bm.Buffers = append(bm.Buffers, buf)
}

// RemoveBuffer removes a buffer/tab by index
func (bm *BuffersManager) RemoveBuffer(index int) {
	if index >= 0 && index < len(bm.Buffers) {
		bm.Buffers = append(bm.Buffers[:index], bm.Buffers[index+1:]...)
	}
}

// SwitchBuffer switches to a buffer/tab by index
func (bm *BuffersManager) SwitchBuffer(index int) {
	if index >= 0 && index < len(bm.Buffers) {
		bm.ActiveBuffer = index
	}
}
