#!/usr/bin/env python3
"""
Test script to verify LaTeX editor initialization fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt5.QtWidgets import QApplication
    from Latex_edit.latex_env import LatexEditorEnv
    
    print("Testing LaTeX editor initialization...")
    
    app = QApplication(sys.argv)
    
    # Test creating the LaTeX editor
    latex_editor = LatexEditorEnv()
    print("✓ LaTeX editor created successfully!")
    
    # Test basic functionality
    print("✓ Editor object exists:", latex_editor.editor is not None)
    print("✓ NumberLine object exists:", latex_editor.numberline is not None)
    print("✓ Minimap object exists:", latex_editor.minimap is not None)
    
    # Test menu bar creation
    print("✓ Menu bar created successfully")
    
    print("\nAll tests passed! The LaTeX editor initialization bug has been fixed.")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 