# Advanced Loading System

The Advanced Loading System is designed to handle large files efficiently in the Third Edit editor. It provides memory-efficient loading, progress indicators, and chunked processing for files that exceed the default threshold of 1000 lines.

## Features

### Automatic Detection
- **Line Threshold**: Files with more than 1000 lines automatically trigger advanced loading
- **Memory Threshold**: Files larger than 50MB automatically use advanced loading
- **Encoding Detection**: Automatically detects and handles different file encodings (UTF-8, Latin-1, CP1252, ISO-8859-1)

### Progress Indicators
- Real-time progress bar showing loading percentage
- Line count display (e.g., "Loading... 1,500 / 3,000 lines (50%)")
- Live preview of loaded content
- Cancelable loading process

### Memory Management
- Chunked loading to prevent memory overflow
- Configurable chunk size (100-10,000 lines per chunk)
- Efficient line counting without loading entire file into memory

### User Interface
- **Advanced Loading Dialog**: Shows file information and loading options
- **Preview Panel**: Displays the last 50 loaded lines in real-time
- **Loading Options**: Configurable chunk size and preview settings
- **Error Handling**: Graceful handling of encoding issues and file errors

## Usage

### Automatic Usage
When you open a file through the normal "Open File" menu or file tree, the system automatically detects if advanced loading is needed:

1. **Small Files** (< 1000 lines): Load normally without any dialog
2. **Large Files** (≥ 1000 lines): Show the Advanced Loading Dialog

### Manual Usage
You can force advanced loading for any file using:

**Tools → Open Large File (Advanced Loading)**

This option bypasses the size check and always uses the advanced loading system.

### Advanced Loading Dialog

When a large file is detected, the Advanced Loading Dialog appears with:

#### File Information
- File name and size
- Line count (if available)
- Detected encoding

#### Loading Options
- **Lines per chunk**: Adjust chunk size (100-10,000 lines)
- **Show preview**: Enable/disable real-time preview

#### Progress Section
- Progress bar showing completion percentage
- Status label with current/total lines
- Cancel button to stop loading

#### Preview Panel
- Shows the last 50 loaded lines
- Updates in real-time as chunks are loaded
- Scrolls to bottom automatically

## Configuration

### Default Settings
```python
DEFAULT_LINE_THRESHOLD = 1000      # Lines before advanced loading
DEFAULT_CHUNK_SIZE = 1000          # Lines per chunk
DEFAULT_MEMORY_LIMIT = 50 * 1024 * 1024  # 50MB file size limit
```

### Customizing Thresholds
You can modify the thresholds in `advancedloading.py`:

```python
# In advancedloading.py
DEFAULT_LINE_THRESHOLD = 2000      # Increase to 2000 lines
DEFAULT_CHUNK_SIZE = 500           # Decrease chunk size
DEFAULT_MEMORY_LIMIT = 100 * 1024 * 1024  # Increase to 100MB
```

## File Types Supported

The advanced loading system works with all text-based file types:

- **Text Files**: `.txt`, `.md`, `.log`, etc.
- **Code Files**: `.py`, `.js`, `.java`, `.cpp`, etc.
- **Data Files**: `.json`, `.csv`, `.xml`, `.yaml`, etc.
- **Configuration Files**: `.ini`, `.cfg`, `.conf`, etc.

## Technical Details

### File Analysis
The `FileAnalyzer` class performs efficient analysis:
1. Checks file size first (fastest check)
2. Counts lines without loading entire file
3. Detects encoding automatically
4. Returns analysis results

### Chunked Loading
The `ChunkedFileLoader` class:
1. Runs in a separate thread to prevent UI freezing
2. Counts total lines in first pass
3. Loads content in configurable chunks
4. Emits progress signals for UI updates
5. Handles cancellation gracefully

### Memory Efficiency
- Only loads one chunk at a time into memory
- Processes files line-by-line without storing entire content
- Uses efficient string operations
- Supports cancellation to free memory immediately

## Error Handling

The system handles various error conditions:

### Encoding Errors
- Automatically tries multiple encodings
- Falls back to binary file handling if needed
- Shows clear error messages

### File Access Errors
- Permission denied errors
- File not found errors
- Corrupted file handling

### Memory Errors
- Out of memory conditions
- Large file handling
- Chunk size optimization

## Testing

Use the provided test script to generate large files:

```bash
python test_large_file.py
```

This creates:
- `large_test_file.txt` (1500 lines)
- `large_test_data.json` (1000 objects)
- `large_test_data.csv` (2000 rows)

## Integration

The advanced loading system is fully integrated into the main editor:

### Main Integration Points
1. **File Opening**: `open_file_in_editor_tab()` method
2. **Menu Integration**: Tools menu with manual option
3. **Tab Management**: Seamless integration with existing tab system
4. **Theme Support**: Respects current editor theme

### Fallback Behavior
If the advanced loading module is not available:
1. Falls back to normal file loading
2. Shows warning message
3. Continues with standard editor functionality

## Performance Considerations

### For Large Files (>10,000 lines)
- Consider increasing chunk size for faster loading
- Monitor memory usage
- Use preview mode sparingly for very large files

### For Very Large Files (>100,000 lines)
- The system may take time to count lines initially
- Consider using the chunked editor mode
- Monitor system resources

## Troubleshooting

### Common Issues

**"Advanced loading module not available"**
- Ensure `advancedloading.py` is in the same directory as `main.py`
- Check for import errors in the console

**"Failed to load file"**
- Check file permissions
- Verify file is not corrupted
- Try different encoding settings

**Slow loading**
- Reduce chunk size
- Disable preview for very large files
- Check available system memory

### Debug Mode
To enable debug output, modify the logging in `advancedloading.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential improvements for future versions:

1. **Virtual Scrolling**: Only render visible lines for extremely large files
2. **Search Integration**: Efficient search across large files
3. **Syntax Highlighting**: Optimized highlighting for large files
4. **Memory Mapping**: Use memory-mapped files for very large datasets
5. **Background Processing**: Load additional chunks in background
6. **Compression Support**: Handle compressed files directly

## Support

For issues or questions about the advanced loading system:
1. Check the console for error messages
2. Verify file permissions and encoding
3. Test with smaller files first
4. Review the configuration settings 