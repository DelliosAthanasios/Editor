/* Every action in the editor will be also mapped to a keybinding
here. The app will be completly customizable and the user will be able to
change the keybindings to their liking. The keybindings will be stored in a
file and loaded at startup. The user will be able to reset the keybindings
to default or save their own keybindings. The keybindings will be used to
perform actions in the editor like opening files, saving files, undoing,
redoing, cutting, copying, pasting, selecting all, searching, replacing,
and more. The keybindings will be used in conjunction with the menu and
toolbar to provide a complete and customizable user experience.
I repeat every actrion in the editor will be mapped to a keybinding.
*/

package keybinds

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
)

// Keybinding represents a mapping from an action to a key
//
type Keybinding struct {
	Action string `json:"action"`
	Key    string `json:"key"`
}

// KeybindManager manages all keybindings
//
type KeybindManager struct {
	Bindings []Keybinding `json:"bindings"`
}

// LoadKeybindings loads keybindings from a file
func (km *KeybindManager) LoadKeybindings(filename string) error {
	if _, err := os.Stat(filename); os.IsNotExist(err) {
		fmt.Printf("Keybindings file %s does not exist, using defaults\n", filename)
		return nil
	}
	
	data, err := ioutil.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("error reading keybindings file: %v", err)
	}
	
	err = json.Unmarshal(data, km)
	if err != nil {
		return fmt.Errorf("error parsing keybindings file: %v", err)
	}
	
	fmt.Printf("Loaded %d keybindings from %s\n", len(km.Bindings), filename)
	return nil
}

// SaveKeybindings saves keybindings to a file
func (km *KeybindManager) SaveKeybindings(filename string) error {
	data, err := json.MarshalIndent(km, "", "  ")
	if err != nil {
		return fmt.Errorf("error marshaling keybindings: %v", err)
	}
	
	err = ioutil.WriteFile(filename, data, 0644)
	if err != nil {
		return fmt.Errorf("error writing keybindings file: %v", err)
	}
	
	fmt.Printf("Saved %d keybindings to %s\n", len(km.Bindings), filename)
	return nil
}

// ResetToDefault resets keybindings to default
func (km *KeybindManager) ResetToDefault() {
	km.Bindings = []Keybinding{
		{Action: "new_file", Key: "Ctrl+N"},
		{Action: "open_file", Key: "Ctrl+O"},
		{Action: "save_file", Key: "Ctrl+S"},
		{Action: "save_all", Key: "Ctrl+Shift+S"},
		{Action: "close_file", Key: "Ctrl+W"},
		{Action: "quit", Key: "Ctrl+Q"},
		{Action: "undo", Key: "Ctrl+Z"},
		{Action: "redo", Key: "Ctrl+Y"},
		{Action: "cut", Key: "Ctrl+X"},
		{Action: "copy", Key: "Ctrl+C"},
		{Action: "paste", Key: "Ctrl+V"},
		{Action: "select_all", Key: "Ctrl+A"},
		{Action: "search", Key: "Ctrl+F"},
		{Action: "replace", Key: "Ctrl+H"},
		{Action: "font_increase", Key: "Ctrl++"},
		{Action: "font_decrease", Key: "Ctrl+-"},
		{Action: "go_to_line_start", Key: "Home"},
		{Action: "go_to_line_end", Key: "End"},
		{Action: "go_to_file_start", Key: "Ctrl+Home"},
		{Action: "go_to_file_end", Key: "Ctrl+End"},
		{Action: "next_word", Key: "Ctrl+Right"},
		{Action: "prev_word", Key: "Ctrl+Left"},
		{Action: "delete_word", Key: "Ctrl+Delete"},
		{Action: "delete_line", Key: "Ctrl+Shift+K"},
		{Action: "next_line", Key: "Down"},
		{Action: "prev_line", Key: "Up"},
		{Action: "next_char", Key: "Right"},
		{Action: "prev_char", Key: "Left"},
	}
	fmt.Println("Keybindings reset to default")
}

// FindKeybinding finds a keybinding by action
func (km *KeybindManager) FindKeybinding(action string) *Keybinding {
	for i := range km.Bindings {
		if km.Bindings[i].Action == action {
			return &km.Bindings[i]
		}
	}
	return nil
}

// FindAction finds an action by key
func (km *KeybindManager) FindAction(key string) string {
	for _, binding := range km.Bindings {
		if binding.Key == key {
			return binding.Action
		}
	}
	return ""
}

// AddKeybinding adds or updates a keybinding
func (km *KeybindManager) AddKeybinding(action, key string) {
	// Check if action already exists
	for i := range km.Bindings {
		if km.Bindings[i].Action == action {
			km.Bindings[i].Key = key
			fmt.Printf("Updated keybinding: %s -> %s\n", action, key)
			return
		}
	}
	
	// Add new keybinding
	km.Bindings = append(km.Bindings, Keybinding{Action: action, Key: key})
	fmt.Printf("Added keybinding: %s -> %s\n", action, key)
}

// RemoveKeybinding removes a keybinding by action
func (km *KeybindManager) RemoveKeybinding(action string) bool {
	for i := range km.Bindings {
		if km.Bindings[i].Action == action {
			km.Bindings = append(km.Bindings[:i], km.Bindings[i+1:]...)
			fmt.Printf("Removed keybinding for action: %s\n", action)
			return true
		}
	}
	fmt.Printf("Keybinding not found for action: %s\n", action)
	return false
}

// ListKeybindings prints all keybindings
func (km *KeybindManager) ListKeybindings() {
	fmt.Println("\n=== Current Keybindings ===")
	for _, binding := range km.Bindings {
		fmt.Printf("  %-20s -> %s\n", binding.Action, binding.Key)
	}
	fmt.Printf("Total: %d keybindings\n\n", len(km.Bindings))
}

// ValidateKeybindings checks for duplicate keys
func (km *KeybindManager) ValidateKeybindings() []string {
	keyMap := make(map[string][]string)
	var conflicts []string
	
	for _, binding := range km.Bindings {
		keyMap[binding.Key] = append(keyMap[binding.Key], binding.Action)
	}
	
	for key, actions := range keyMap {
		if len(actions) > 1 {
			conflicts = append(conflicts, fmt.Sprintf("Key '%s' is bound to multiple actions: %v", key, actions))
		}
	}
	
	return conflicts
}
