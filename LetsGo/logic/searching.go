/*
Here will be the logic of the searching functionality in the application.
We will implement a search function that allows users to fin text within the current file.
The search function will take
1) a search term as input
2) search through the text of the current file ( Let the user deside which algorithm to use, like linear search or regexm or binary search by default use the faster one)
3) Highlite the found text in the file
4) if the user allows it add a replace function that will replace the found text with a new text
5) The user can replace all or just one instance of the found text
6) The user can navigate through the found instances of the text
7) The user can cancel the search operation at any time
8) The search function will be case sensitive or insensitive based on user preference
9) The search function will support regular expressions for advanced searching
*/

package logic

// SearchManager manages searching and replacing in the editor
//
type SearchManager struct {
	CaseSensitive bool
	UseRegex      bool
	Results       []int // Indices of found matches
	CurrentIndex  int   // Current match index
}

// Search searches for a term in the given text
func (sm *SearchManager) Search(text, term string) {
	// Placeholder: Implement search logic (linear, regex, etc.)
	// Update sm.Results with match indices
}

// Replace replaces the current or all found terms with newText
func (sm *SearchManager) Replace(text, newText string, replaceAll bool) string {
	// Placeholder: Implement replace logic
	return text
}

// Next moves to the next found instance
func (sm *SearchManager) Next() {
	if len(sm.Results) > 0 {
		sm.CurrentIndex = (sm.CurrentIndex + 1) % len(sm.Results)
	}
}

// Prev moves to the previous found instance
func (sm *SearchManager) Prev() {
	if len(sm.Results) > 0 {
		sm.CurrentIndex = (sm.CurrentIndex - 1 + len(sm.Results)) % len(sm.Results)
	}
}

// Cancel cancels the search operation
func (sm *SearchManager) Cancel() {
	sm.Results = nil
	sm.CurrentIndex = 0
}
