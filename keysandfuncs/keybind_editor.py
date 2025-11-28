import copy
from typing import Dict, List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QKeySequenceEdit,
    QVBoxLayout,
    QWidget,
)


class KeybindEditorWidget(QWidget):
    """Editor-friendly keybind manager embedded inside a tab."""

    bindingsSaved = pyqtSignal(dict)
    requestClose = pyqtSignal()

    def __init__(self, parent: QWidget, bindings: Dict[str, List[str]], actions: List[dict]):
        super().__init__(parent)
        self.setMinimumSize(520, 520)

        # Work on a copy so Cancel truly cancels.
        self._bindings = copy.deepcopy(bindings)
        self._actions = actions

        self._build_ui()
        self._refresh_binding_list()

    # ------------------------------------------------------------------ UI setup
    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Available Actions")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.action_list = QListWidget()
        self.action_list.setSelectionMode(QAbstractItemView.MultiSelection)
        for action in self._actions:
            item = QListWidgetItem(f"{action['title']} — {action['description']}")
            item.setData(Qt.UserRole, action["id"])
            self.action_list.addItem(item)
        layout.addWidget(self.action_list)

        capture_row = QHBoxLayout()
        capture_row.addWidget(QLabel("Key sequence:"))
        self.key_edit = QKeySequenceEdit()
        capture_row.addWidget(self.key_edit, 1)
        layout.addLayout(capture_row)

        button_row = QHBoxLayout()
        single_btn = QPushButton("Bind Selected")
        single_btn.clicked.connect(self._add_single_binding)
        button_row.addWidget(single_btn)

        combo_btn = QPushButton("Bind Combination")
        combo_btn.clicked.connect(self._add_combined_binding)
        button_row.addWidget(combo_btn)
        layout.addLayout(button_row)

        layout.addWidget(QLabel("Current Bindings"))

        self.binding_list = QListWidget()
        self.binding_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.binding_list, 1)

        remove_btn = QPushButton("Remove Selected Binding")
        remove_btn.clicked.connect(self._remove_selected_binding)
        layout.addWidget(remove_btn)

        tip = QLabel(
            "Tip: select several actions then choose “Bind Combination” "
            "to execute them in order via a single keybind."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #999999; font-size: 11px;")
        layout.addWidget(tip)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._emit_save)
        self.close_btn = QPushButton("Close Editor")
        self.close_btn.clicked.connect(self.requestClose.emit)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------ helpers
    def _current_sequence_text(self) -> str:
        key_sequence = self.key_edit.keySequence()
        if key_sequence.isEmpty():
            return ""
        return key_sequence.toString(QKeySequence.PortableText)

    def _selected_action_ids(self) -> List[str]:
        return [
            item.data(Qt.UserRole)
            for item in self.action_list.selectedItems()
        ]

    def _add_single_binding(self):
        seq = self._current_sequence_text()
        if not seq:
            QMessageBox.warning(self, "Missing Shortcut", "Press a key combination first.")
            return
        action_ids = self._selected_action_ids()
        if len(action_ids) != 1:
            QMessageBox.warning(self, "Select One Action", "Select exactly one action to bind.")
            return
        self._bindings[seq] = action_ids
        self._refresh_binding_list()
        self.key_edit.clear()

    def _add_combined_binding(self):
        seq = self._current_sequence_text()
        if not seq:
            QMessageBox.warning(self, "Missing Shortcut", "Press a key combination first.")
            return
        action_ids = self._selected_action_ids()
        if len(action_ids) < 2:
            QMessageBox.warning(
                self,
                "Need Multiple Actions",
                "Select two or more actions to combine into a single keybind.",
            )
            return
        self._bindings[seq] = action_ids
        self._refresh_binding_list()
        self.key_edit.clear()

    def _remove_selected_binding(self):
        item = self.binding_list.currentItem()
        if not item:
            return
        seq = item.data(Qt.UserRole)
        self._bindings.pop(seq, None)
        self._refresh_binding_list()

    def _refresh_binding_list(self):
        self.binding_list.clear()
        if not self._bindings:
            empty = QListWidgetItem("No bindings defined yet.")
            empty.setFlags(Qt.NoItemFlags)
            self.binding_list.addItem(empty)
            return

        for seq, action_ids in sorted(self._bindings.items()):
            labels = [self._label_for_action(action_id) for action_id in action_ids]
            display = f"{seq} → {', '.join(labels)}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, seq)
            self.binding_list.addItem(item)

    def _label_for_action(self, action_id: str) -> str:
        for action in self._actions:
            if action["id"] == action_id:
                return action["title"]
        return action_id

    # ------------------------------------------------------------------ actions
    def _emit_save(self):
        self.bindingsSaved.emit(self.get_bindings())

    # ------------------------------------------------------------------ public API
    def get_bindings(self) -> Dict[str, List[str]]:
        return copy.deepcopy(self._bindings)

