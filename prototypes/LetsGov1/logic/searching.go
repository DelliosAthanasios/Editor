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

import (
	"fmt"
	"regexp"
	"strings"
)

// SearchManager manages searching and replacing in the editor
//
type SearchManager struct {
	CaseSensitive bool
	UseRegex      bool
	Results       []int // Indices of found matches
	CurrentIndex  int   // Current match index
	LastTerm      string // Last searched term
}

// Search searches for a term in the given text
func (sm *SearchManager) Search(text, term string) {
	if term == "" {
		sm.Results = []int{}
		sm.CurrentIndex = 0
		return
	}
	
	sm.LastTerm = term
	sm.Results = []int{}
	sm.CurrentIndex = 0
	
	searchText := text
	searchTerm := term
	
	// Handle case sensitivity
	if !sm.CaseSensitive {
		searchText = strings.ToLower(text)
		searchTerm = strings.ToLower(term)
	}
	
	if sm.UseRegex {
		// Use regex search
		pattern, err := regexp.Compile(searchTerm)
		if err != nil {
			fmt.Printf("Invalid regex pattern: %v\n", err)
			return
		}
		
		matches := pattern.FindAllStringIndex(searchText, -1)
		for _, match := range matches {
			sm.Results = append(sm.Results, match[0])
		}
	} else {
		// Use linear search (faster for simple text)
		index := 0
		for {
			pos := strings.Index(searchText[index:], searchTerm)
			if pos == -1 {
				break
			}
			actualPos := index + pos
			sm.Results = append(sm.Results, actualPos)
			index = actualPos + 1
		}
	}
	
	fmt.Printf("Found %d matches for '%s'\n", len(sm.Results), term)
	if len(sm.Results) > 0 {
		fmt.Printf("Currently at match 1 of %d\n", len(sm.Results))
	}
}

// Replace replaces the current or all found terms with newText
func (sm *SearchManager) Replace(text, newText string, replaceAll bool) string {
	if len(sm.Results) == 0 {
		fmt.Println("No search results to replace")
		return text
	}
	
	if replaceAll {
		// Replace all occurrences
		result := text
		searchTerm := sm.LastTerm
		
		if !sm.CaseSensitive {
			// For case-insensitive replacement, we need to be more careful
			// This is a simplified implementation
			if sm.UseRegex {
				pattern, err := regexp.Compile("(?i)" + searchTerm)
				if err == nil {
					result = pattern.ReplaceAllString(result, newText)
				}
			} else {
				// Simple case-insensitive replacement
				lowerText := strings.ToLower(result)
				lowerTerm := strings.ToLower(searchTerm)
				
				var newResult strings.Builder
				lastIndex := 0
				
				for {
					index := strings.Index(lowerText[lastIndex:], lowerTerm)
					if index == -1 {
						newResult.WriteString(result[lastIndex:])
						break
					}
					
					actualIndex := lastIndex + index
					newResult.WriteString(result[lastIndex:actualIndex])
					newResult.WriteString(newText)
					lastIndex = actualIndex + len(searchTerm)
				}
				result = newResult.String()
			}
		} else {
			// Case-sensitive replacement
			if sm.UseRegex {
				pattern, err := regexp.Compile(searchTerm)
				if err == nil {
					result = pattern.ReplaceAllString(result, newText)
				}
			} else {
				result = strings.ReplaceAll(result, searchTerm, newText)
			}
		}
		
		fmt.Printf("Replaced all %d occurrences\n", len(sm.Results))
		// Clear results after replace all
		sm.Results = []int{}
		sm.CurrentIndex = 0
		return result
	} else {
		// Replace only current match
		if sm.CurrentIndex >= 0 && sm.CurrentIndex < len(sm.Results) {
			pos := sm.Results[sm.CurrentIndex]
			termLen := len(sm.LastTerm)
			
			// Replace at the specific position
			result := text[:pos] + newText + text[pos+termLen:]
			
			fmt.Printf("Replaced match %d of %d\n", sm.CurrentIndex+1, len(sm.Results))
			
			// Update remaining result positions
			lenDiff := len(newText) - termLen
			for i := sm.CurrentIndex + 1; i < len(sm.Results); i++ {
				sm.Results[i] += lenDiff
			}
			
			// Remove current match from results
			sm.Results = append(sm.Results[:sm.CurrentIndex], sm.Results[sm.CurrentIndex+1:]...)
			if sm.CurrentIndex >= len(sm.Results) && len(sm.Results) > 0 {
				sm.CurrentIndex = len(sm.Results) - 1
			}
			
			return result
		}
	}
	
	return text
}

// Next moves to the next found instance
func (sm *SearchManager) Next() {
	if len(sm.Results) > 0 {
		sm.CurrentIndex = (sm.CurrentIndex + 1) % len(sm.Results)
		fmt.Printf("Moved to match %d of %d\n", sm.CurrentIndex+1, len(sm.Results))
	} else {
		fmt.Println("No search results available")
	}
}

// Prev moves to the previous found instance
func (sm *SearchManager) Prev() {
	if len(sm.Results) > 0 {
		sm.CurrentIndex = (sm.CurrentIndex - 1 + len(sm.Results)) % len(sm.Results)
		fmt.Printf("Moved to match %d of %d\n", sm.CurrentIndex+1, len(sm.Results))
	} else {
		fmt.Println("No search results available")
	}
}

// Cancel cancels the search operation
func (sm *SearchManager) Cancel() {
	sm.Results = []int{}
	sm.CurrentIndex = 0
	sm.LastTerm = ""
	fmt.Println("Search cancelled")
}

// GetCurrentMatch returns the current match position
func (sm *SearchManager) GetCurrentMatch() int {
	if sm.CurrentIndex >= 0 && sm.CurrentIndex < len(sm.Results) {
		return sm.Results[sm.CurrentIndex]
	}
	return -1
}

// HasResults returns true if there are search results
func (sm *SearchManager) HasResults() bool {
	return len(sm.Results) > 0
}
