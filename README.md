# MCP Server Collection

This repository contains multiple Model Context Protocol (MCP) servers built with FastMCP.

## Quick Setup

1. **Environment is ready:**
   ```bash
   cd ~/mcp-server
   # Virtual environment is already set up at .venv/
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys (especially TAVILY_API_KEY)
   ```

3. **Use with MCP clients:**
   - Copy `mcp.json` to your MCP client configuration directory
   - Or use servers directly: `mcp dev ftp/ftp_server.py` or `mcp dev tavily-internet/tavily_server.py`


## License

This project is part of the MCP ecosystem and follows the same licensing terms.


## Bonus
### Small patch inside Mantis

at `Mantis/Decoys/FTP/fake_ftp_tarpit.py`:

```py
def handle_cwd(self, client_socket, current_path, data, client_data_connection_info, injection_manager):
    """Handle the CWD command to change directories."""
    # Old
    client_ip, client_port = client_data_connection_info
    #
    new_dir = data.split(' ')[1] if len(data.split(' ')) > 1 else '/'
    if new_dir == '/':
        new_path = '/'
    else:
        new_path = current_path.rstrip('/') + '/' + new_dir

    msg = b"250 Directory successfully changed\r\n"
    msg, _ = injection_manager((client_ip, client_port), self.source_name, self.name+'.continue', msg)
    msg += b'\r\n'
    client_socket.sendall(msg)
    
    return new_path
```

replace with

```py
def handle_cwd(self, client_socket, current_path, data, client_data_connection_info, injection_manager):
    """Handle the CWD command to change directories."""
    # New
    # Check if client_data_connection_info is available
    if client_data_connection_info is not None:
        client_ip, client_port = client_data_connection_info
    else:
        client_ip, client_port = None, None
    #
    new_dir = data.split(' ')[1] if len(data.split(' ')) > 1 else '/'
    if new_dir == '/':
        new_path = '/'
    else:
        new_path = current_path.rstrip('/') + '/' + new_dir

    msg = b"250 Directory successfully changed\r\n"
    msg, _ = injection_manager((client_ip, client_port), self.source_name, self.name+'.continue', msg)
    msg += b'\r\n'
    client_socket.sendall(msg)
    
    return new_path
```

### Setup with PentestAgent (VI)
Đầu tiên, clone thư mục này về máy, ghi nhận lại thư mục hiện tại bằng cách gõ `pwd`

Setup môi trường:
```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Sau khi đã tải đủ các gói như
```
sudo apt update && sudo apt install -y amass arjun assetfinder ffuf httpx hydra masscan metasploit-framework nmap nuclei sqlmap 
sudo apt install -y postgresql postgresql-contrib golang-go
```

Load các biến môi trường này (tùy chọn)
```
# Set up local Go environment (using project-local .go directory)
export GOPATH="$PWD/.go"
export GOBIN="$PWD/.go/bin"
export PATH="$PWD/.go/bin:$PATH"
```

Tải thêm các gói sau:
```
CGO_ENABLED=1 go install github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
```

Để mở Metasploit server, gõ lệnh sau ở thư mục đã clone:
```
scripts/start-services
```

Kiểm tra service và đóng service tương tự như vậy.

Vào trong `python main.py`:
* Không chọn knowledge base
* Tạo mới các tool sau: 7,9,11,12,13,16 (tương ứng với các tool: httpx, katana, metasploit, nmap, nuclei, sqlmap)
* Bấm yes khi nó thấy PATH. Metasploit server có password là 1, các trường còn lại để mặc định

Sau khi chương trình đã tạo được mcp.json, vào trong đó và thêm mục sau: (với /root/mcp-server là địa chỉ thư mục đã clone, chỉnh sửa lại)
```
{
  "servers": [
    {
      "name": "tavily-internet",
      "params": {
        "command": "/root/mcp-server/.venv/bin/python", 
        "args": ["/root/mcp-server/tavily-internet/tavily_server.py"],
        "description": "Tavily Internet Search MCP - AI-powered web search with content extraction and Q&A capabilities",
        "env": {
          "PYTHONPATH": "/root/mcp-server",
          "TAVILY_API_KEY": "<tavily-api-key>",
          "_comment": "Ensure to set the TAVILY_API_KEY environment variable with your actual API key"
        }
      },
      "cache_tools_list": true
    },
    {
      "name": "ftp",
      "params": {
        "command": "/root/mcp-server/.venv/bin/python",
        "args": ["/root/mcp-server/ftp/ftp_server.py"],
        "description": "FTP Server MCP - Complete FTP operations including connection, file transfer, and directory management",
        "env": {
            "PYTHONPATH": "/root/mcp-server"
        }
      },
      "cache_tools_list": true
    },
    ...
  ]
}
```

Ở lần tới chạy, chỉ cần mở `python main.py`, chọn kết nối vào các tool, đã xong