#!/usr/bin/env python3
"""
Test script to verify the advanced loading functionality.
This script tests the advanced loading system without opening the GUI.
"""

import os
import sys
import tempfile
import time

def test_file_analyzer():
    """Test the FileAnalyzer class"""
    print("Testing FileAnalyzer...")
    
    try:
        from advancedloading import FileAnalyzer
        
        # Create a test file with exactly 1000 lines
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(1000):
                f.write(f"Line {i+1}: Test content\n")
            test_file = f.name
        
        analyzer = FileAnalyzer()
        
        # Test with 1000 lines (should not trigger advanced loading)
        should_use, file_info = analyzer.should_use_advanced_loading(test_file)
        print(f"1000 lines file: should_use={should_use}, lines={file_info.get('lines')}")
        assert not should_use, "1000 lines should not trigger advanced loading"
        
        # Create a test file with 1001 lines (should trigger advanced loading)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(1001):
                f.write(f"Line {i+1}: Test content\n")
            test_file_large = f.name
        
        should_use, file_info = analyzer.should_use_advanced_loading(test_file_large)
        print(f"1001 lines file: should_use={should_use}, lines={file_info.get('lines')}")
        assert should_use, "1001 lines should trigger advanced loading"
        
        # Cleanup
        os.unlink(test_file)
        os.unlink(test_file_large)
        
        print("✅ FileAnalyzer tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ FileAnalyzer test failed: {e}")
        return False

def test_chunked_loader():
    """Test the ChunkedFileLoader class"""
    print("Testing ChunkedFileLoader...")
    
    try:
        from advancedloading import ChunkedFileLoader
        from PyQt5.QtCore import QCoreApplication, QEventLoop, QTimer
        
        # Create QApplication if not exists
        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication(sys.argv)
        
        # Create a test file with 1500 lines
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(1500):
                f.write(f"Line {i+1}: Test content for chunked loading\n")
            test_file = f.name
        
        # Test the loader
        loader = ChunkedFileLoader(test_file, chunk_size=500)
        
        chunks_received = []
        progress_updates = []
        loading_finished = False
        
        def on_chunk_loaded(chunk):
            chunks_received.append(chunk)
            print(f"Received chunk {len(chunks_received)} with {len(chunk)} lines")
        
        def on_progress_updated(current, total):
            progress_updates.append((current, total))
            print(f"Progress: {current}/{total} lines")
        
        def on_loading_finished():
            nonlocal loading_finished
            loading_finished = True
            print("Loading finished!")
        
        # Connect signals
        loader.chunk_loaded.connect(on_chunk_loaded)
        loader.progress_updated.connect(on_progress_updated)
        loader.loading_finished.connect(on_loading_finished)
        
        # Start loading
        loader.start()
        
        # Wait for completion with timeout
        timeout = 10  # 10 seconds timeout
        start_time = time.time()
        
        while not loading_finished and (time.time() - start_time) < timeout:
            app.processEvents()
            time.sleep(0.1)
        
        if not loading_finished:
            print("❌ Loading timed out")
            return False
        
        # Verify results
        print(f"Received {len(chunks_received)} chunks")
        print(f"Progress updates: {len(progress_updates)}")
        
        # For 1500 lines with 500 line chunks, we should get 3 chunks
        expected_chunks = 3
        assert len(chunks_received) == expected_chunks, f"Expected {expected_chunks} chunks, got {len(chunks_received)}"
        
        # Verify chunk sizes (last chunk might be smaller)
        assert len(chunks_received[0]) == 500, f"First chunk should have 500 lines, got {len(chunks_received[0])}"
        assert len(chunks_received[1]) == 500, f"Second chunk should have 500 lines, got {len(chunks_received[1])}"
        assert len(chunks_received[2]) == 500, f"Third chunk should have 500 lines, got {len(chunks_received[2])}"
        
        # Cleanup
        os.unlink(test_file)
        
        print("✅ ChunkedFileLoader tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ ChunkedFileLoader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    try:
        from advancedloading import CONFIG, load_config
        
        # Test that config is loaded
        assert 'line_threshold' in CONFIG, "line_threshold should be in config"
        assert 'chunk_size' in CONFIG, "chunk_size should be in config"
        assert 'memory_limit_mb' in CONFIG, "memory_limit_mb should be in config"
        
        print(f"Config loaded: line_threshold={CONFIG['line_threshold']}, "
              f"chunk_size={CONFIG['chunk_size']}, "
              f"memory_limit_mb={CONFIG['memory_limit_mb']}")
        
        print("✅ Configuration loading tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading test failed: {e}")
        return False

def test_should_use_advanced_loading():
    """Test the convenience function"""
    print("Testing should_use_advanced_loading function...")
    
    try:
        from advancedloading import should_use_advanced_loading
        
        # Create test files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(999):
                f.write(f"Line {i+1}\n")
            small_file = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for i in range(1001):
                f.write(f"Line {i+1}\n")
            large_file = f.name
        
        # Test small file
        should_use, file_info = should_use_advanced_loading(small_file)
        assert not should_use, "Small file should not use advanced loading"
        
        # Test large file
        should_use, file_info = should_use_advanced_loading(large_file)
        assert should_use, "Large file should use advanced loading"
        
        # Cleanup
        os.unlink(small_file)
        os.unlink(large_file)
        
        print("✅ should_use_advanced_loading tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ should_use_advanced_loading test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Advanced Loading System")
    print("=" * 50)
    
    tests = [
        test_config_loading,
        test_file_analyzer,
        test_chunked_loader,
        test_should_use_advanced_loading,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Advanced loading system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 