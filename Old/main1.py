import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QAction, QFileDialog,
    QTextEdit, QStyleFactory, QTabWidget, QWidget, QHBoxLayout
)
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter
from PyQt5.QtCore import Qt, QTimer

class Minimap(QWidget):
    def __init__(self, parent, text_widget: QTextEdit, linenumbers=None):
        super().__init__(parent)
        self.setFixedWidth(100)
        self.setAutoFillBackground(True)
        self.text_widget = text_widget
        self.linenumbers = linenumbers

        self.font_name = "Courier New"
        self.font_size = 6
        self.line_spacing = 9
        self.max_line_length = 50
        self.last_y = 0

        self.setMouseTracking(True)

        self.text_widget.viewport().installEventFilter(self)
        self.text_widget.document().contentsChanged.connect(self.schedule_update)
        self.text_widget.verticalScrollBar().valueChanged.connect(self.schedule_update)

        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_minimap)

    def schedule_update(self):
        self.update_timer.start(50)

    def update_minimap(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2e2e2e"))

        height = self.height()
        total_lines = self.text_widget.document().blockCount()
        lines_to_render = int(height / self.line_spacing)

        first_visible = self.text_widget.cursorForPosition(self.text_widget.viewport().rect().topLeft()).blockNumber()
        last_visible = min(first_visible + lines_to_render, total_lines)

        font = QFont(self.font_name, self.font_size)
        painter.setFont(font)
        painter.setPen(QColor("#909090"))

        block = self.text_widget.document().findBlockByNumber(first_visible)
        for idx in range(first_visible, last_visible):
            y_pos = (idx - first_visible) * self.line_spacing
            text = block.text().replace('\t', '    ')[:self.max_line_length]
            painter.drawText(2, y_pos + self.font_size, text)
            block = block.next()

        if self.linenumbers and self.linenumbers.isVisible():
            self.linenumbers.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.scroll_to_click(event.y())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.on_drag(event.y())

    def wheelEvent(self, event):
        direction = -1 if event.angleDelta().y() > 0 else 1
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().value() + direction * 3
        )
        self.schedule_update()

    def scroll_to_click(self, y):
        total_lines = self.text_widget.document().blockCount()
        rel_y = y / self.height()
        target_line = max(0, min(int(rel_y * total_lines), total_lines - 1))
        cursor = self.text_widget.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, cursor.MoveAnchor, target_line)
        self.text_widget.setTextCursor(cursor)
        self.text_widget.centerCursor()
        self.last_y = y
        self.schedule_update()

    def on_drag(self, y):
        delta = (y - self.last_y) * 2
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().value() + int(-delta)
        )
        self.last_y = y
        self.schedule_update()

    def eventFilter(self, obj, event):
        self.schedule_update()
        return super().eventFilter(obj, event)

class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Third Edit")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyle(QStyleFactory.create("Fusion"))

        self.init_ui()
        self.set_dark_theme()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.add_new_tab()
        self.setCentralWidget(self.tabs)
        self.create_menu_bar()

    def add_new_tab(self, title="Untitled"):
        editor = QTextEdit()
        editor.setFont(QFont("Fira Code", 12))
        minimap = Minimap(self, editor)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(editor)
        layout.addWidget(minimap)

        index = self.tabs.addTab(container, title)
        self.tabs.setCurrentIndex(index)

    def close_tab(self, index):
        self.tabs.removeTab(index)

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("New File",self.new_file)
        file_menu.addAction("Open File", self.open_file)
       # file_menu.addAction("Close File")
        file_menu.addAction("Save File",self.save_file)
        file_menu.addAction("Dublicate File",self.dublicate_file)
        file_menu.addSeparator()
        file_menu.addAction("New Tab", lambda: self.add_new_tab())
        file_menu.addAction("Close Tab", lambda: self.close_tab(self.tabs.currentIndex()))

        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Undo")
        edit_menu.addAction("Redo")
        edit_menu.addAction("Select All")
        search_menu = edit_menu.addMenu("Search")
        search_menu.addAction("Replace")
        go_to_menu = edit_menu.addMenu("Go To")
        go_to_menu.addAction("Line")
        go_to_menu.addAction("Word")
        checkpoints_menu = edit_menu.addMenu("Checkpoints")
        checkpoints_menu.addAction("Create Checkpoint")
        checkpoints_menu.addAction("Go to Checkpoint")

        view_menu = menu_bar.addMenu("View")
        view_menu.addAction("Toggle Number Line")
        view_menu.addAction("Rotate Number Line")
        view_menu.addAction("Toggle Minimap")
        view_menu.addAction("Toggle File Menu")
        split_screen_menu = view_menu.addMenu("Split Screen")
        Themes_screen_menu = view_menu.addMenu("Themes")
        Themes_screen_menu.addAction("White Mode", self.set_light_theme)
        Themes_screen_menu.addAction("Dark Mode", self.set_dark_theme)
        split_screen_menu.addAction("Horizontal Split")
        split_screen_menu.addAction("Vertical Split")

        options_menu = menu_bar.addMenu("Options")
        options_menu.addAction("Fonts")
        options_menu.addAction("Theme Manager")
        options_menu.addAction("Extensions")

        keybind_menu = menu_bar.addMenu("Keybinds")
        keybind_menu.addAction("Configure Keybinds")
        keybind_menu.addAction("Default Keybinds Map")

        languages_menu = menu_bar.addMenu("Languages")
        languages_menu.addAction("Syntax Options")
        languages_menu.addAction("Compilers")

        env_menu = menu_bar.addMenu("Environments")
        env_menu.addAction("Create Environment")
        env_menu.addAction("Configure Environment")
        env_menu.addAction("Create Custom Environment")

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("Documentation")
        help_menu.addAction("Tutorial")
        help_menu.addAction("About Developer")

        tools_menu = menu_bar.addMenu("Tools")
        tools_menu.addAction("Process Manager")
        tools_menu.addAction("Control Panel")
        tools_menu.addAction("Open PDF")
        tools_menu.addAction("Open Image")
        tools_menu.addAction("View Editor Source Code")

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File")
        if file_name:
            with open(file_name, 'r') as f:
                content = f.read()
            self.add_new_tab(title=file_name.split('/')[-1])
            current_editor = self.tabs.currentWidget().layout().itemAt(0).widget()
            current_editor.setPlainText(content)

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.Highlight, QColor(100, 100, 255))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)

        self.setStyleSheet("""
            QMenuBar { background-color: #2b2b2b; color: white; }
            QMenuBar::item:selected { background: #44475a; }
            QMenu { background-color: #2b2b2b; color: white; }
            QMenu::item:selected { background-color: #44475a; }
        """)
def new_file(self):
    try:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Create New File", "", 
            "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
        )
        if file_path:
            open(file_path, 'w').close()  # Create empty file
            self.add_new_tab(title=os.path.basename(file_path))
    except Exception as e:
        QMessageBox.critical(self, "Error", "Invalid Creation request: " + str(e))

def save_file(self):
    current_widget = self.tabs.currentWidget()
    if not current_widget: return
    
    editor = current_widget.layout().itemAt(0).widget()
    content = editor.toPlainText()
    
    file_path, _ = QFileDialog.getSaveFileName(
        self, "Save File", "",
        "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
    )
    if file_path:
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")

def duplicate_file(self):
    current_widget = self.tabs.currentWidget()
    if not current_widget: return
    
    editor = current_widget.layout().itemAt(0).widget()
    content = editor.toPlainText()
    
    original_path = self.tabs.tabText(self.tabs.currentIndex())
    if original_path == "Untitled":
        QMessageBox.warning(self, "Warning", "Please save the file before duplicating")
        return

    base_path = os.path.splitext(original_path)[0]
    extension = os.path.splitext(original_path)[1]
    counter = 1
    new_path = f"{base_path}_duplicate{extension}"

    while os.path.exists(new_path):
        new_path = f"{base_path}_duplicate{counter}{extension}"
        counter += 1

    try:
        with open(new_path, 'w') as f:
            f.write(content)
        self.add_new_tab(title=os.path.basename(new_path))
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Duplication failed: {str(e)}")

    def set_light_theme(self):
        QApplication.setPalette(QApplication.style().standardPalette())
        self.setStyleSheet("")
'''
   Pseudocode
   def newfile():
   When file menu New file button is pressed:
   open a new window similar UI to already existing app
   Create dialog box
   Name of the new file
   Create dialog box
   File type(support types txt and programming languages)
   Create button( browse computer) (location of that new file))
   Create button (Create)
   Initiate changes (use the python try functions so when error ocurs print the message" Invalid Creation request")
'''
'''
 Pseudocode
 def save_file():
 When file_menu_save_file button is pressed:
 Open windows File browser(Like the Open_button)with an extra save file button
 The user can choose the reposatory or folder and save the file
'''
'''
def dublicate_file():
when file_menu_dublicate_file button is pressed:
Open a window which lists all the open tabs in the editor
Create button Dublicate
Create button Cancel
The user can choose which tab he wants to dublicate
on button press dublicate:
Copy the selected file
Rename it as ("nameofthefile"_dublicate)
and save the file in the location of the original file
if the ("nameofthefile"_dublicate) already exists:
Create a list of natural numbers N=[]
Check if after _dublicate there is a number
if there_is_a_number=False
then print _dublicate2
if there_is_a_number=True
save the value of the number
then print _dublicate+L[readed value of the number]

Example
if dublicate3
it will read the 3 save it
and it will print dublicate+N[3]
N[3] is for because python lists start from 0
so the result is dublicate4

'''

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TextEditor()
    window.show()
    sys.exit(app.exec_())
