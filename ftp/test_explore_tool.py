#!/usr/bin/env python3
"""
Quick test for the new ftp_explore_directory tool.
"""

import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_explore_directory():
    """Test the new explore directory tool."""
    
    server_params = StdioServerParameters(
        command="/root/mcp-server/.venv/bin/python",
        args=["ftp_server.py"],
        env=os.environ.copy()
    )
    
    print("🧪 Testing ftp_explore_directory tool")
    print("=" * 50)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            await session.initialize()
            print("✅ MCP Session initialized")
            
            # Connect to FTP server
            print("\n📡 Connecting to FTP server at 10.0.0.100...")
            try:
                connect_result = await session.call_tool(
                    "ftp_connect",
                    {
                        "connection_id": "test_server",
                        "host": "10.0.0.100",
                        "username": "anonymous",
                        "password": "",
                        "port": 21,
                        "passive": True
                    }
                )
                print(f"Connection: {connect_result.content[0].text}")
                
                if "failed" in connect_result.content[0].text.lower():
                    print("❌ Connection failed")
                    return
                    
            except Exception as e:
                print(f"❌ Connection error: {e}")
                return
            
            # Test exploring root directory
            print("\n📁 Test 1: Exploring root directory '/'...")
            try:
                explore_result = await session.call_tool("ftp_explore_directory", {
                    "directory": "/"
                })
                
                if hasattr(explore_result.content[0], 'text'):
                    print(f"Result: {explore_result.content[0].text}")
                else:
                    import json
                    result_data = json.loads(str(explore_result.content[0]))
                    print("Exploration Results:")
                    for key, value in result_data.items():
                        print(f"  {key}: {value}")
                        
            except Exception as e:
                print(f"❌ Explore root error: {e}")
            
            # Test exploring a common directory
            print("\n📁 Test 2: Exploring '/pub' directory...")
            try:
                explore_result = await session.call_tool("ftp_explore_directory", {
                    "directory": "/pub"
                })
                
                if hasattr(explore_result.content[0], 'text'):
                    print(f"Result: {explore_result.content[0].text}")
                else:
                    import json
                    result_data = json.loads(str(explore_result.content[0]))
                    print("Exploration Results:")
                    for key, value in result_data.items():
                        print(f"  {key}: {value}")
                        
            except Exception as e:
                print(f"❌ Explore /pub error: {e}")
            
            # Test exploring a non-existent directory
            print("\n📁 Test 3: Exploring non-existent directory '/nonexistent'...")
            try:
                explore_result = await session.call_tool("ftp_explore_directory", {
                    "directory": "/nonexistent"
                })
                
                if hasattr(explore_result.content[0], 'text'):
                    print(f"Result: {explore_result.content[0].text}")
                else:
                    import json
                    result_data = json.loads(str(explore_result.content[0]))
                    print("Exploration Results:")
                    for key, value in result_data.items():
                        print(f"  {key}: {value}")
                        
            except Exception as e:
                print(f"❌ Explore nonexistent error: {e}")
            
            # Test exploring current directory
            print("\n📁 Test 4: Exploring current directory '.'...")
            try:
                explore_result = await session.call_tool("ftp_explore_directory", {
                    "directory": "."
                })
                
                if hasattr(explore_result.content[0], 'text'):
                    print(f"Result: {explore_result.content[0].text}")
                else:
                    import json
                    result_data = json.loads(str(explore_result.content[0]))
                    print("Exploration Results:")
                    for key, value in result_data.items():
                        print(f"  {key}: {value}")
                        
            except Exception as e:
                print(f"❌ Explore current directory error: {e}")
            
            # Disconnect
            print("\n🔌 Disconnecting...")
            try:
                disconnect_result = await session.call_tool("ftp_disconnect", {})
                print(f"Disconnect: {disconnect_result.content[0].text}")
            except Exception as e:
                print(f"❌ Disconnect error: {e}")
            
            print("\n✅ ftp_explore_directory testing completed!")


if __name__ == "__main__":
    asyncio.run(test_explore_directory())