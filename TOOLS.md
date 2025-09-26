## Available Servers

### 1. FTP MCP Server (`ftp/`)

A comprehensive Model Context Protocol (MCP) server for FTP operations, providing full FTP functionality including connection management, file transfers, and directory operations.

## Features

### Connection Management
- **Connect to FTP servers** with authentication
- **Multiple connection support** - manage multiple FTP connections simultaneously
- **Connection switching** - easily switch between active connections
- **Passive/Active mode** support
- **Connection status monitoring**

### Directory Operations
- **List directories** with detailed file information
- **Change directories** (cd/cwd)
- **Get current directory** (pwd)
- **Create directories** (mkdir)
- **Remove directories** (rmdir)
- **Create directory trees** (recursive directory creation)

### File Operations
- **Upload files** from local filesystem
- **Upload content** directly from text/binary data
- **Download files** to local filesystem
- **Download content** directly to memory
- **Delete files**
- **Rename files and directories**
- **Get file size and modification time**

### Advanced Features
- **Binary and text transfer modes**
- **Progress reporting** for operations
- **Server system information**
- **Connection keep-alive** (NOOP)
- **Error handling** with detailed messages
- **Multiple encoding support**

## Installation

1. Make sure you have Python 3.8+ installed
2. Install the MCP Python SDK:

```bash
pip install "mcp[cli]"
```

## Usage

### Running the Server

```bash
# Direct execution
python ftp_server.py

# Or with MCP tools
uv run mcp dev ftp_server.py
```

### Available Tools** (23 total):

#### Connection Management
- `ftp_connect` - Connect to FTP server
- `ftp_disconnect` - Disconnect from FTP server
- `ftp_list_connections` - List all active connections
- `ftp_switch_connection` - Switch between connections

#### Directory Operations
- `ftp_pwd` - Get current working directory
- `ftp_cwd` - Change working directory
- `ftp_explore_directory` - Explore directory with navigation status (cd only, no listing)
- `ftp_list_directory` - List directory contents with details
- `ftp_mkdir` - Create directory
- `ftp_rmdir` - Remove directory
- `ftp_create_directory_tree` - Create directory tree recursively

#### File Operations
- `ftp_upload_file` - Upload file from local filesystem
- `ftp_upload_content` - Upload content directly
- `ftp_download_file` - Download file to local filesystem
- `ftp_download_content` - Download file content to memory
- `ftp_delete_file` - Delete file
- `ftp_rename` - Rename file or directory
- `ftp_get_file_size` - Get file size information

#### Advanced Operations
- `ftp_set_passive_mode` - Toggle passive/active mode
- `ftp_get_system_info` - Get server system information
- `ftp_send_noop` - Send keep-alive command
- `ftp_get_modification_time` - Get file modification time
- `ftp_transfer_progress` - Get transfer information

### Available Resources

- `ftp://connections` - Current FTP connections status
- `ftp://current-directory` - Current working directory
- `ftp://server-info` - FTP server information

## Examples

### Basic Connection and Operations

```python
# Connect to FTP server
await session.call_tool("ftp_connect", {
    "connection_id": "main_server",
    "host": "ftp.example.com",
    "username": "your_username",
    "password": "your_password",
    "port": 21,
    "passive": True
})

# List current directory
listing = await session.call_tool("ftp_list_directory", {
    "detailed": True
})

# Upload a file
upload_result = await session.call_tool("ftp_upload_file", {
    "local_path": "/path/to/local/file.txt",
    "remote_path": "remote_file.txt",
    "binary_mode": False
})

# Download a file
download_result = await session.call_tool("ftp_download_file", {
    "remote_path": "remote_file.txt",
    "local_path": "/path/to/local/downloaded_file.txt"
})

# Explore a directory (navigation only, no listing)
explore_result = await session.call_tool("ftp_explore_directory", {
    "directory": "/pub/documents"
})
# Returns status information: accessible, can_navigate, can_go_up, etc.
```

### Multiple Connections

```python
# Connect to multiple servers
await session.call_tool("ftp_connect", {
    "connection_id": "server1",
    "host": "ftp1.example.com",
    "username": "user1",
    "password": "pass1"
})

await session.call_tool("ftp_connect", {
    "connection_id": "server2", 
    "host": "ftp2.example.com",
    "username": "user2",
    "password": "pass2"
})

# Switch between connections
await session.call_tool("ftp_switch_connection", {
    "connection_id": "server2"
})

# List all connections
connections = await session.call_tool("ftp_list_connections", {})
```

### Content Operations

```python
# Upload content directly
await session.call_tool("ftp_upload_content", {
    "content": "Hello, World!",
    "remote_path": "greeting.txt",
    "binary_mode": False
})

# Download content to memory
content = await session.call_tool("ftp_download_content", {
    "remote_path": "greeting.txt",
    "binary_mode": False,
    "max_size_mb": 1
})
```

## Error Handling

The server provides comprehensive error handling:

- **Connection errors** - Invalid credentials, network issues
- **File operation errors** - Permission denied, file not found
- **Protocol errors** - Unsupported commands, server limitations
- **Graceful fallbacks** - Alternative methods when primary commands fail

## Security Considerations

- **Password security** - Passwords are not logged or exposed in error messages
- **File size limits** - Configurable limits for content downloads
- **Path validation** - Basic protection against path traversal
- **Connection cleanup** - Automatic cleanup of connections on server shutdown

## Testing

Run the demo script to test functionality:

```bash
python ftp_demo.py
```

This will:
1. Start the MCP server
2. Demonstrate various tools
3. Show available resources
4. Create sample files for testing

### 2. Tavily Internet Search MCP Server (`tavily-internet/`)

AI-powered internet search server using Tavily API for comprehensive web search, content extraction, and Q&A capabilities.

#### Features
- **Web Search** - Search the internet with AI-powered results
- **Content Extraction** - Extract content from specific URLs
- **Search Context** - Get condensed context for RAG applications
- **Q&A Search** - Direct question-answering with sources
- **Multiple Topics** - General, news, and finance search categories
- **Advanced Filtering** - Include/exclude domains, date ranges

#### Setup
```bash
# Set your Tavily API key in .env
TAVILY_API_KEY=your-tavily-api-key-here

# Test the server
python tavily-internet/test_tavily_server.py
```

#### Available Tools (4 total):
- `tavily_search` - General web search with comprehensive results
- `tavily_extract_content` - Extract content from specific URLs
- `tavily_get_search_context` - Get search context for RAG
- `tavily_qna_search` - Q&A focused search with direct answers

#### Available Resources:
- `tavily://status` - API connection status and health check
- `tavily://usage` - API usage information and limits

## Requirements

- Python 3.8+
- MCP Python SDK
- `tavily-python` - For Tavily internet search server
- Standard library modules: `ftplib`, `os`, `io`, `base64`, `datetime`

## Troubleshooting

### Common Issues

1. **Connection timeout** - Check network connectivity and firewall settings
2. **Passive mode issues** - Try switching to active mode with `ftp_set_passive_mode`
3. **Permission errors** - Verify FTP user permissions
4. **Encoding issues** - Specify correct encoding for text transfers

### Debug Mode

Run with debug logging:

```bash
python ftp_server.py --debug
```