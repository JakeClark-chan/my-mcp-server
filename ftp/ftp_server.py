#!/usr/bin/env python3
"""
MCP Server for FTP operations.

Provides comprehensive FTP functionality including:
- Connection management (connect, login, disconnect)
- Directory operations (ls, cd, pwd, mkdir, rmdir)
- File operations (upload, download, delete, rename)
- Advanced features (permissions, status, passive/active mode)
"""

import asyncio
import base64
import ftplib
import io
import os
import stat
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field


@dataclass
class FTPContext:
    """Application context for FTP connections."""
    connections: Dict[str, ftplib.FTP]
    current_connection: Optional[str]


@asynccontextmanager
async def ftp_lifespan(server: FastMCP) -> AsyncIterator[FTPContext]:
    """Manage FTP connections lifecycle."""
    connections = {}
    try:
        yield FTPContext(connections=connections, current_connection=None)
    finally:
        # Clean up all connections on shutdown
        for conn_id, ftp in connections.items():
            try:
                ftp.quit()
            except Exception:
                try:
                    ftp.close()
                except Exception:
                    pass
        connections.clear()


# Initialize the MCP server
mcp = FastMCP("FTP Server", lifespan=ftp_lifespan)


class FTPConnectionInfo(BaseModel):
    """FTP connection information."""
    host: str = Field(description="FTP server hostname or IP")
    port: int = Field(default=21, description="FTP server port")
    username: str = Field(description="FTP username")
    password: str = Field(description="FTP password")
    passive: bool = Field(default=True, description="Use passive mode")


class FTPFileInfo(BaseModel):
    """FTP file information."""
    name: str
    type: str  # 'file' or 'directory'
    size: Optional[int] = None
    modified: Optional[str] = None
    permissions: Optional[str] = None


class FTPDirectoryListing(BaseModel):
    """FTP directory listing result."""
    current_directory: str
    files: List[FTPFileInfo]
    total_files: int
    total_directories: int


@mcp.tool()
async def ftp_connect(
    connection_id: str,
    host: str,
    username: str,
    password: str,
    port: int = 21,
    passive: bool = True,
    timeout: int = 30,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Connect to an FTP server and authenticate.
    
    Args:
        connection_id: Unique identifier for this connection
        host: FTP server hostname or IP address
        username: FTP username
        password: FTP password
        port: FTP server port (default: 21)
        passive: Use passive mode (default: True)
        timeout: Connection timeout in seconds (default: 30)
    
    Returns:
        Connection status message
    """
    try:
        await ctx.info(f"Connecting to FTP server {host}:{port}")
        
        # Create new FTP connection
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout)
        
        # Set passive mode
        ftp.set_pasv(passive)
        
        # Login
        await ctx.info(f"Logging in as {username}")
        ftp.login(username, password)
        
        # Store connection
        ctx.request_context.lifespan_context.connections[connection_id] = ftp
        ctx.request_context.lifespan_context.current_connection = connection_id
        
        # Get welcome message
        welcome = ftp.getwelcome()
        
        await ctx.info(f"Successfully connected to {host}")
        
        return f"Connected to {host}:{port} as {username}. Welcome message: {welcome}"
        
    except ftplib.error_perm as e:
        await ctx.error(f"Authentication failed: {e}")
        return f"Authentication failed: {e}"
    except Exception as e:
        await ctx.error(f"Connection failed: {e}")
        return f"Connection failed: {e}"


@mcp.tool()
async def ftp_disconnect(
    connection_id: Optional[str] = None,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Disconnect from FTP server.
    
    Args:
        connection_id: Connection ID to disconnect (uses current if not specified)
    
    Returns:
        Disconnection status message
    """
    try:
        # Use current connection if not specified
        if connection_id is None:
            connection_id = ctx.request_context.lifespan_context.current_connection
            
        if not connection_id:
            return "No active connection to disconnect"
            
        connections = ctx.request_context.lifespan_context.connections
        
        if connection_id not in connections:
            return f"Connection '{connection_id}' not found"
            
        ftp = connections[connection_id]
        
        try:
            ftp.quit()
        except Exception:
            ftp.close()
            
        # Remove from connections
        del connections[connection_id]
        
        # Update current connection
        if ctx.request_context.lifespan_context.current_connection == connection_id:
            # Set to another connection if available, otherwise None
            remaining_connections = list(connections.keys())
            ctx.request_context.lifespan_context.current_connection = (
                remaining_connections[0] if remaining_connections else None
            )
            
        await ctx.info(f"Disconnected from {connection_id}")
        return f"Successfully disconnected from {connection_id}"
        
    except Exception as e:
        await ctx.error(f"Error disconnecting: {e}")
        return f"Error disconnecting: {e}"


@mcp.tool()
async def ftp_list_connections(
    ctx: Context[ServerSession, FTPContext] = None
) -> Dict[str, str]:
    """
    List all active FTP connections.
    
    Returns:
        Dictionary of connection IDs and their status
    """
    connections = ctx.request_context.lifespan_context.connections
    current = ctx.request_context.lifespan_context.current_connection
    
    result = {}
    for conn_id, ftp in connections.items():
        try:
            # Test connection with NOOP
            ftp.voidcmd("NOOP")
            status = "Active"
            if conn_id == current:
                status += " (Current)"
        except Exception:
            status = "Disconnected"
            
        result[conn_id] = status
        
    return result


@mcp.tool()
async def ftp_switch_connection(
    connection_id: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Switch to a different active connection.
    
    Args:
        connection_id: Connection ID to switch to
        
    Returns:
        Switch status message
    """
    connections = ctx.request_context.lifespan_context.connections
    
    if connection_id not in connections:
        return f"Connection '{connection_id}' not found"
        
    # Test if connection is still active
    try:
        ftp = connections[connection_id]
        ftp.voidcmd("NOOP")
        ctx.request_context.lifespan_context.current_connection = connection_id
        return f"Switched to connection '{connection_id}'"
    except Exception as e:
        return f"Connection '{connection_id}' is no longer active: {e}"


def _get_current_ftp(ctx: Context[ServerSession, FTPContext]) -> ftplib.FTP:
    """Get the current FTP connection or raise an error."""
    current_id = ctx.request_context.lifespan_context.current_connection
    if not current_id:
        raise ValueError("No active FTP connection. Use ftp_connect first.")
        
    connections = ctx.request_context.lifespan_context.connections
    if current_id not in connections:
        raise ValueError(f"Connection '{current_id}' not found")
        
    return connections[current_id]


@mcp.tool()
async def ftp_pwd(ctx: Context[ServerSession, FTPContext] = None) -> str:
    """
    Get current working directory on FTP server.
    
    Returns:
        Current directory path
    """
    try:
        ftp = _get_current_ftp(ctx)
        current_dir = ftp.pwd()
        return current_dir
    except Exception as e:
        await ctx.error(f"Error getting current directory: {e}")
        return f"Error: {e}"


@mcp.tool()
async def ftp_cwd(
    directory: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Change working directory on FTP server.
    
    Args:
        directory: Directory path to change to
        
    Returns:
        Status message with new directory
    """
    try:
        ftp = _get_current_ftp(ctx)
        ftp.cwd(directory)
        new_dir = ftp.pwd()
        await ctx.info(f"Changed directory to {new_dir}")
        return f"Changed to directory: {new_dir}"
    except Exception as e:
        await ctx.error(f"Error changing directory: {e}")
        return f"Error changing directory: {e}"


@mcp.tool()
async def ftp_explore_directory(
    directory: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> Dict[str, Union[str, bool]]:
    """
    Explore a directory by changing to it and returning status information.
    This tool only navigates without listing contents for quick directory exploration.
    
    Args:
        directory: Directory path to explore
        
    Returns:
        Dictionary with exploration status and directory information
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        # Store original directory in case we need to go back
        original_dir = ftp.pwd()
        
        # Try to change to the directory
        try:
            ftp.cwd(directory)
            new_dir = ftp.pwd()
            
            # Check if we can navigate (basic permissions test)
            can_navigate = True
            navigation_status = "Directory accessible"
            
            # Try to go up one level to test navigation permissions
            try:
                ftp.cwd("..")
                parent_dir = ftp.pwd()
                # Go back to the target directory
                ftp.cwd(new_dir)
                can_go_up = True
                parent_accessible = True
            except Exception:
                can_go_up = False
                parent_accessible = False
                
            await ctx.info(f"Successfully explored directory: {new_dir}")
            
            return {
                "success": True,
                "directory": new_dir,
                "original_directory": original_dir,
                "accessible": True,
                "can_navigate": can_navigate,
                "can_go_up": can_go_up,
                "parent_accessible": parent_accessible,
                "status": navigation_status,
                "message": f"Successfully changed to {new_dir}"
            }
            
        except ftplib.error_perm as e:
            # Directory change failed
            error_msg = str(e).lower()
            
            if "no such file" in error_msg or "not found" in error_msg:
                status = "Directory does not exist"
            elif "permission denied" in error_msg or "access denied" in error_msg:
                status = "Permission denied"
            elif "not a directory" in error_msg:
                status = "Path is not a directory"
            else:
                status = f"Access error: {e}"
                
            await ctx.warning(f"Cannot access directory {directory}: {status}")
            
            return {
                "success": False,
                "directory": directory,
                "original_directory": original_dir,
                "accessible": False,
                "can_navigate": False,
                "can_go_up": False,
                "parent_accessible": False,
                "status": status,
                "message": f"Cannot access {directory}: {status}",
                "error": str(e)
            }
            
    except Exception as e:
        await ctx.error(f"Error exploring directory: {e}")
        return {
            "success": False,
            "directory": directory,
            "original_directory": "unknown",
            "accessible": False,
            "can_navigate": False,
            "can_go_up": False,
            "parent_accessible": False,
            "status": "Exploration failed",
            "message": f"Error exploring directory: {e}",
            "error": str(e)
        }


@mcp.tool()
async def ftp_list_directory(
    directory: Optional[str] = None,
    detailed: bool = True,
    ctx: Context[ServerSession, FTPContext] = None
) -> FTPDirectoryListing:
    """
    List files and directories on FTP server.
    
    Args:
        directory: Directory to list (current directory if not specified)
        detailed: Include detailed file information
        
    Returns:
        Directory listing with file information
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        # Change to directory if specified
        original_dir = ftp.pwd()
        if directory:
            ftp.cwd(directory)
            
        current_dir = ftp.pwd()
        
        files = []
        total_files = 0
        total_directories = 0
        
        if detailed:
            # Use MLSD if available for detailed listings
            try:
                for name, facts in ftp.mlsd():
                    if name in ['.', '..']:
                        continue
                        
                    file_type = facts.get('type', 'file')
                    size = facts.get('size')
                    modified = facts.get('modify')
                    
                    # Convert modify time format
                    if modified:
                        try:
                            dt = datetime.strptime(modified, '%Y%m%d%H%M%S')
                            modified = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            pass
                    
                    file_info = FTPFileInfo(
                        name=name,
                        type='directory' if file_type == 'dir' else 'file',
                        size=int(size) if size else None,
                        modified=modified,
                        permissions=facts.get('perm')
                    )
                    
                    files.append(file_info)
                    
                    if file_type == 'dir':
                        total_directories += 1
                    else:
                        total_files += 1
                        
            except ftplib.error_perm:
                # Fall back to LIST command
                await ctx.warning("MLSD not supported, using LIST command")
                listing = []
                ftp.retrlines('LIST', listing.append)
                
                for line in listing:
                    if not line.strip():
                        continue
                        
                    # Parse Unix-style listing
                    parts = line.split()
                    if len(parts) >= 9:
                        permissions = parts[0]
                        size_str = parts[4]
                        name = ' '.join(parts[8:])
                        
                        if name in ['.', '..']:
                            continue
                            
                        # Determine file type from permissions
                        file_type = 'directory' if permissions.startswith('d') else 'file'
                        
                        # Parse size
                        try:
                            size = int(size_str) if file_type == 'file' else None
                        except ValueError:
                            size = None
                            
                        # Parse date (simplified)
                        try:
                            month, day, year_or_time = parts[5], parts[6], parts[7]
                            if ':' in year_or_time:
                                # Current year, time given
                                year = datetime.now().year
                                modified = f"{year}-{month}-{day} {year_or_time}"
                            else:
                                # Year given
                                modified = f"{year_or_time}-{month}-{day}"
                        except (IndexError, ValueError):
                            modified = None
                            
                        file_info = FTPFileInfo(
                            name=name,
                            type=file_type,
                            size=size,
                            modified=modified,
                            permissions=permissions
                        )
                        
                        files.append(file_info)
                        
                        if file_type == 'directory':
                            total_directories += 1
                        else:
                            total_files += 1
        else:
            # Simple listing
            names = ftp.nlst()
            for name in names:
                if name in ['.', '..']:
                    continue
                    
                # Try to determine if it's a directory
                try:
                    original_pwd = ftp.pwd()
                    ftp.cwd(name)
                    ftp.cwd(original_pwd)
                    file_type = 'directory'
                    total_directories += 1
                except ftplib.error_perm:
                    file_type = 'file'
                    total_files += 1
                    
                file_info = FTPFileInfo(name=name, type=file_type)
                files.append(file_info)
        
        # Return to original directory if we changed it
        if directory:
            ftp.cwd(original_dir)
            
        return FTPDirectoryListing(
            current_directory=current_dir,
            files=sorted(files, key=lambda x: (x.type == 'file', x.name.lower())),
            total_files=total_files,
            total_directories=total_directories
        )
        
    except Exception as e:
        await ctx.error(f"Error listing directory: {e}")
        raise


@mcp.tool()
async def ftp_mkdir(
    directory: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Create a directory on FTP server.
    
    Args:
        directory: Directory name/path to create
        
    Returns:
        Status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        ftp.mkd(directory)
        await ctx.info(f"Created directory: {directory}")
        return f"Successfully created directory: {directory}"
    except Exception as e:
        await ctx.error(f"Error creating directory: {e}")
        return f"Error creating directory: {e}"


@mcp.tool()
async def ftp_rmdir(
    directory: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Remove a directory on FTP server.
    
    Args:
        directory: Directory name/path to remove
        
    Returns:
        Status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        ftp.rmd(directory)
        await ctx.info(f"Removed directory: {directory}")
        return f"Successfully removed directory: {directory}"
    except Exception as e:
        await ctx.error(f"Error removing directory: {e}")
        return f"Error removing directory: {e}"


@mcp.tool()
async def ftp_delete_file(
    filename: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Delete a file on FTP server.
    
    Args:
        filename: File name/path to delete
        
    Returns:
        Status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        ftp.delete(filename)
        await ctx.info(f"Deleted file: {filename}")
        return f"Successfully deleted file: {filename}"
    except Exception as e:
        await ctx.error(f"Error deleting file: {e}")
        return f"Error deleting file: {e}"


@mcp.tool()
async def ftp_rename(
    old_name: str,
    new_name: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Rename a file or directory on FTP server.
    
    Args:
        old_name: Current name/path
        new_name: New name/path
        
    Returns:
        Status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        ftp.rename(old_name, new_name)
        await ctx.info(f"Renamed {old_name} to {new_name}")
        return f"Successfully renamed {old_name} to {new_name}"
    except Exception as e:
        await ctx.error(f"Error renaming: {e}")
        return f"Error renaming: {e}"


@mcp.tool()
async def ftp_upload_file(
    local_path: str,
    remote_path: Optional[str] = None,
    binary_mode: bool = True,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Upload a file to FTP server.
    
    Args:
        local_path: Local file path to upload
        remote_path: Remote file path (uses local filename if not specified)
        binary_mode: Use binary transfer mode (default: True)
        
    Returns:
        Upload status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        if not os.path.exists(local_path):
            return f"Local file not found: {local_path}"
            
        if not os.path.isfile(local_path):
            return f"Path is not a file: {local_path}"
            
        # Use filename from local path if remote path not specified
        if remote_path is None:
            remote_path = os.path.basename(local_path)
            
        file_size = os.path.getsize(local_path)
        await ctx.info(f"Uploading {local_path} to {remote_path} ({file_size} bytes)")
        
        with open(local_path, 'rb' if binary_mode else 'r') as file:
            if binary_mode:
                ftp.storbinary(f'STOR {remote_path}', file)
            else:
                ftp.storlines(f'STOR {remote_path}', file)
                
        await ctx.info(f"Successfully uploaded {local_path}")
        return f"Successfully uploaded {local_path} to {remote_path} ({file_size} bytes)"
        
    except Exception as e:
        await ctx.error(f"Error uploading file: {e}")
        return f"Error uploading file: {e}"


@mcp.tool()
async def ftp_upload_content(
    content: str,
    remote_path: str,
    binary_mode: bool = False,
    encoding: str = 'utf-8',
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Upload content directly to FTP server.
    
    Args:
        content: Content to upload
        remote_path: Remote file path
        binary_mode: Use binary transfer mode
        encoding: Text encoding (used when binary_mode=False)
        
    Returns:
        Upload status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        if binary_mode:
            # Handle binary content (expect base64 encoded)
            try:
                content_bytes = base64.b64decode(content)
            except Exception:
                return "Content must be base64 encoded for binary mode"
            file_obj = io.BytesIO(content_bytes)
            ftp.storbinary(f'STOR {remote_path}', file_obj)
            size = len(content_bytes)
        else:
            # Handle text content
            content_bytes = content.encode(encoding)
            file_obj = io.BytesIO(content_bytes)
            ftp.storbinary(f'STOR {remote_path}', file_obj)
            size = len(content_bytes)
            
        await ctx.info(f"Uploaded content to {remote_path} ({size} bytes)")
        return f"Successfully uploaded content to {remote_path} ({size} bytes)"
        
    except Exception as e:
        await ctx.error(f"Error uploading content: {e}")
        return f"Error uploading content: {e}"


@mcp.tool()
async def ftp_download_file(
    remote_path: str,
    local_path: Optional[str] = None,
    binary_mode: bool = True,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Download a file from FTP server.
    
    Args:
        remote_path: Remote file path to download
        local_path: Local file path (uses remote filename if not specified)
        binary_mode: Use binary transfer mode (default: True)
        
    Returns:
        Download status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        # Use filename from remote path if local path not specified
        if local_path is None:
            local_path = os.path.basename(remote_path)
            
        # Create directory if it doesn't exist
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
            
        await ctx.info(f"Downloading {remote_path} to {local_path}")
        
        with open(local_path, 'wb' if binary_mode else 'w') as file:
            if binary_mode:
                ftp.retrbinary(f'RETR {remote_path}', file.write)
            else:
                ftp.retrlines(f'RETR {remote_path}', file.write)
                
        file_size = os.path.getsize(local_path)
        await ctx.info(f"Successfully downloaded {remote_path}")
        return f"Successfully downloaded {remote_path} to {local_path} ({file_size} bytes)"
        
    except Exception as e:
        await ctx.error(f"Error downloading file: {e}")
        return f"Error downloading file: {e}"


@mcp.tool()
async def ftp_download_content(
    remote_path: str,
    binary_mode: bool = False,
    encoding: str = 'utf-8',
    max_size_mb: int = 10,
    ctx: Context[ServerSession, FTPContext] = None
) -> Dict[str, Union[str, int]]:
    """
    Download file content directly from FTP server.
    
    Args:
        remote_path: Remote file path to download
        binary_mode: Use binary transfer mode (returns base64 encoded)
        encoding: Text encoding (used when binary_mode=False)
        max_size_mb: Maximum file size to download in MB
        
    Returns:
        Dictionary with content and metadata
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        # Check file size first
        try:
            size = ftp.size(remote_path)
            if size and size > max_size_mb * 1024 * 1024:
                return {
                    "error": f"File too large ({size} bytes). Maximum allowed: {max_size_mb}MB",
                    "size": size
                }
        except ftplib.error_perm:
            # SIZE command not supported, continue anyway
            pass
            
        await ctx.info(f"Downloading content from {remote_path}")
        
        # Download content to memory
        content_io = io.BytesIO()
        ftp.retrbinary(f'RETR {remote_path}', content_io.write)
        content_bytes = content_io.getvalue()
        
        if binary_mode:
            # Return base64 encoded content for binary files
            content = base64.b64encode(content_bytes).decode('ascii')
        else:
            # Return text content
            content = content_bytes.decode(encoding)
            
        return {
            "content": content,
            "size": len(content_bytes),
            "binary_mode": binary_mode,
            "encoding": encoding if not binary_mode else "base64"
        }
        
    except Exception as e:
        await ctx.error(f"Error downloading content: {e}")
        return {"error": str(e)}


@mcp.tool()
async def ftp_get_file_size(
    remote_path: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> Dict[str, Union[str, int]]:
    """
    Get file size on FTP server.
    
    Args:
        remote_path: Remote file path
        
    Returns:
        File size information
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        try:
            size = ftp.size(remote_path)
            return {
                "file": remote_path,
                "size": size,
                "size_mb": round(size / (1024 * 1024), 2) if size else 0
            }
        except ftplib.error_perm as e:
            if "not a regular file" in str(e).lower():
                return {"file": remote_path, "error": "Not a regular file (possibly a directory)"}
            else:
                return {"file": remote_path, "error": f"SIZE command failed: {e}"}
                
    except Exception as e:
        await ctx.error(f"Error getting file size: {e}")
        return {"file": remote_path, "error": str(e)}


@mcp.tool()
async def ftp_set_passive_mode(
    passive: bool,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Set passive/active mode for FTP connection.
    
    Args:
        passive: True for passive mode, False for active mode
        
    Returns:
        Status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        ftp.set_pasv(passive)
        mode = "passive" if passive else "active"
        await ctx.info(f"Set FTP mode to {mode}")
        return f"FTP mode set to {mode}"
    except Exception as e:
        await ctx.error(f"Error setting FTP mode: {e}")
        return f"Error setting FTP mode: {e}"


@mcp.tool()
async def ftp_get_system_info(
    ctx: Context[ServerSession, FTPContext] = None
) -> Dict[str, str]:
    """
    Get FTP server system information.
    
    Returns:
        Server system information
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        info = {}
        
        # Get system type
        try:
            system = ftp.sendcmd('SYST')
            info['system'] = system
        except Exception as e:
            info['system'] = f"Error: {e}"
            
        # Get status
        try:
            status = ftp.sendcmd('STAT')
            info['status'] = status
        except Exception as e:
            info['status'] = f"Error: {e}"
            
        # Get features (if supported)
        try:
            features = ftp.sendcmd('FEAT')
            info['features'] = features
        except Exception as e:
            info['features'] = f"FEAT not supported: {e}"
            
        # Get welcome message
        info['welcome'] = ftp.getwelcome()
        
        return info
        
    except Exception as e:
        await ctx.error(f"Error getting system info: {e}")
        return {"error": str(e)}


@mcp.tool()
async def ftp_send_noop(
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Send NOOP command to keep connection alive.
    
    Returns:
        Server response
    """
    try:
        ftp = _get_current_ftp(ctx)
        response = ftp.voidcmd('NOOP')
        return f"NOOP response: {response}"
    except Exception as e:
        await ctx.error(f"Error sending NOOP: {e}")
        return f"Error: {e}"


@mcp.tool()
async def ftp_get_modification_time(
    remote_path: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> Dict[str, str]:
    """
    Get file modification time on FTP server.
    
    Args:
        remote_path: Remote file path
        
    Returns:
        File modification time information
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        try:
            # MDTM command returns time in YYYYMMDDHHMMSS format
            mdtm_response = ftp.sendcmd(f'MDTM {remote_path}')
            
            # Parse response (format: "213 YYYYMMDDHHMMSS")
            time_str = mdtm_response.split()[-1]
            
            # Convert to readable format
            dt = datetime.strptime(time_str, '%Y%m%d%H%M%S')
            readable_time = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            return {
                "file": remote_path,
                "modification_time": readable_time,
                "raw_time": time_str
            }
            
        except ftplib.error_perm as e:
            return {"file": remote_path, "error": f"MDTM command failed: {e}"}
            
    except Exception as e:
        await ctx.error(f"Error getting modification time: {e}")
        return {"file": remote_path, "error": str(e)}


@mcp.tool()
async def ftp_create_directory_tree(
    directory_path: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Create directory tree (including parent directories).
    
    Args:
        directory_path: Full directory path to create
        
    Returns:
        Status message
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        # Split path into components
        parts = directory_path.strip('/').split('/')
        current_path = ''
        
        created_dirs = []
        
        for part in parts:
            if not part:
                continue
                
            current_path = f"{current_path}/{part}" if current_path else part
            
            try:
                # Try to create the directory
                ftp.mkd(current_path)
                created_dirs.append(current_path)
                await ctx.info(f"Created directory: {current_path}")
            except ftplib.error_perm as e:
                if "exists" in str(e).lower():
                    # Directory already exists, continue
                    continue
                else:
                    # Other error, stop here
                    raise e
                    
        if created_dirs:
            return f"Successfully created directories: {', '.join(created_dirs)}"
        else:
            return f"Directory path already exists: {directory_path}"
            
    except Exception as e:
        await ctx.error(f"Error creating directory tree: {e}")
        return f"Error creating directory tree: {e}"


@mcp.tool()
async def ftp_transfer_progress(
    operation: str,
    ctx: Context[ServerSession, FTPContext] = None
) -> str:
    """
    Get information about transfer capabilities and modes.
    
    Args:
        operation: Type of operation info ('modes', 'capabilities', 'status')
        
    Returns:
        Transfer information
    """
    try:
        ftp = _get_current_ftp(ctx)
        
        if operation == 'modes':
            # Check current passive mode status
            try:
                # There's no direct way to check passive mode, so we'll check the connection
                return f"Current connection active. Passive mode can be toggled with ftp_set_passive_mode."
            except Exception as e:
                return f"Error checking modes: {e}"
                
        elif operation == 'capabilities':
            # Get server capabilities
            try:
                feat_response = ftp.sendcmd('FEAT')
                return f"Server capabilities:\n{feat_response}"
            except Exception as e:
                return f"FEAT command not supported: {e}"
                
        elif operation == 'status':
            # Get connection status
            try:
                status = ftp.sendcmd('STAT')
                return f"Connection status:\n{status}"
            except Exception as e:
                return f"Error getting status: {e}"
                
        else:
            return f"Unknown operation: {operation}. Use 'modes', 'capabilities', or 'status'."
            
    except Exception as e:
        await ctx.error(f"Error getting transfer info: {e}")
        return f"Error: {e}"


# Resources for connection status and server information
@mcp.resource("ftp://connections")
async def get_connections_status(ctx: Context[ServerSession, FTPContext] = None) -> str:
    """Get current FTP connections status."""
    connections = ctx.request_context.lifespan_context.connections
    current = ctx.request_context.lifespan_context.current_connection
    
    if not connections:
        return "No active FTP connections."
        
    status_lines = ["Active FTP Connections:"]
    
    for conn_id, ftp in connections.items():
        try:
            ftp.voidcmd("NOOP")
            status = "✓ Connected"
            if conn_id == current:
                status += " (Current)"
        except Exception:
            status = "✗ Disconnected"
            
        status_lines.append(f"  {conn_id}: {status}")
        
    return "\n".join(status_lines)


@mcp.resource("ftp://current-directory")
async def get_current_directory(ctx: Context[ServerSession, FTPContext] = None) -> str:
    """Get current working directory of active FTP connection."""
    try:
        ftp = _get_current_ftp(ctx)
        current_dir = ftp.pwd()
        return f"Current directory: {current_dir}"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error getting current directory: {e}"


@mcp.resource("ftp://server-info")
async def get_server_info(ctx: Context[ServerSession, FTPContext] = None) -> str:
    """Get FTP server information for current connection."""
    try:
        ftp = _get_current_ftp(ctx)
        
        info_lines = ["FTP Server Information:"]
        
        # Welcome message
        welcome = ftp.getwelcome()
        if welcome:
            info_lines.append(f"Welcome: {welcome}")
            
        # System info
        try:
            system = ftp.sendcmd('SYST')
            info_lines.append(f"System: {system}")
        except Exception:
            info_lines.append("System: Not available")
            
        # Current directory
        try:
            pwd = ftp.pwd()
            info_lines.append(f"Current Directory: {pwd}")
        except Exception:
            info_lines.append("Current Directory: Not available")
            
        return "\n".join(info_lines)
        
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error getting server info: {e}"


if __name__ == "__main__":
    mcp.run()