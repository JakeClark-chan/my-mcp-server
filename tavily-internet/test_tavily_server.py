#!/usr/bin/env python3
"""
Test script for Tavily Internet MCP Server.
Tests all available tools and resources.
"""

import asyncio
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file if it exists."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value

# Load .env file at startup
load_env()


async def test_tavily_server():
    """Test the Tavily MCP server functionality."""
    
    # Check if API key is available
    api_key = os.getenv('TAVILY_API_KEY')
    if not api_key:
        print("⚠️  No TAVILY_API_KEY environment variable found.")
        print("   Set your API key to test actual searches:")
        print("   export TAVILY_API_KEY='your_api_key_here'")
        print()
    
    # Server parameters
    server_params = StdioServerParameters(
        command="/root/mcp-server/.venv/bin/python",
        args=["/root/mcp-server/tavily-internet/tavily_server.py"],
        env=os.environ.copy()
    )
    
    print("🧪 Testing Tavily Internet MCP Server")
    print("=" * 50)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize the session
            await session.initialize()
            print("✅ MCP Session initialized")
            
            # List available tools
            print("\n📋 Available Tools:")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  • {tool.name}: {tool.description}")
            
            # List available resources
            print("\n📁 Available Resources:")
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"  • {resource.uri}: {resource.name}")
            
            # Test resources first (works without API key)
            print("\n📄 Testing Resources...")
            
            # Test status resource
            try:
                status_resource = await session.read_resource("tavily://status")
                print(f"Status: {status_resource.contents[0].text}")
            except Exception as e:
                print(f"❌ Status resource error: {e}")
            
            # Test usage resource
            try:
                usage_resource = await session.read_resource("tavily://usage")
                print(f"Usage Info: {usage_resource.contents[0].text[:200]}...")
            except Exception as e:
                print(f"❌ Usage resource error: {e}")
            
            # Only test search tools if API key is available
            if api_key:
                print("\n🔍 Testing Search Tools...")
                
                # Test basic search
                print("\n1. Testing tavily_search...")
                try:
                    search_result = await session.call_tool(
                        "tavily_search",
                        {
                            "query": "Python programming language latest features",
                            "search_depth": "basic",
                            "max_results": 3,
                            "include_answer": True,
                            "include_images": False
                        }
                    )
                    
                    if hasattr(search_result.content[0], 'text'):
                        print(f"Search result: {search_result.content[0].text[:200]}...")
                    else:
                        import json
                        result_data = json.loads(str(search_result.content[0]))
                        print(f"Query: {result_data.get('query', 'N/A')}")
                        print(f"Answer: {result_data.get('answer', 'N/A')[:100]}...")
                        print(f"Results count: {result_data.get('total_results', 0)}")
                        
                except Exception as e:
                    print(f"❌ Search error: {e}")
                
                # Test Q&A search
                print("\n2. Testing tavily_qna_search...")
                try:
                    qna_result = await session.call_tool(
                        "tavily_qna_search",
                        {
                            "query": "What is the latest version of Python?",
                            "search_depth": "basic",
                            "max_results": 2
                        }
                    )
                    
                    if hasattr(qna_result.content[0], 'text'):
                        print(f"Q&A result: {qna_result.content[0].text[:200]}...")
                    else:
                        import json
                        result_data = json.loads(str(qna_result.content[0]))
                        print(f"Question: {result_data.get('query', 'N/A')}")
                        print(f"Answer: {result_data.get('answer', 'N/A')[:100]}...")
                        
                except Exception as e:
                    print(f"❌ Q&A search error: {e}")
                
                # Test search context
                print("\n3. Testing tavily_get_search_context...")
                try:
                    context_result = await session.call_tool(
                        "tavily_get_search_context",
                        {
                            "query": "Machine learning basics",
                            "max_tokens": 1000,
                            "search_depth": "basic"
                        }
                    )
                    
                    if hasattr(context_result.content[0], 'text'):
                        print(f"Context result: {context_result.content[0].text[:200]}...")
                    else:
                        import json
                        result_data = json.loads(str(context_result.content[0]))
                        print(f"Context length: {result_data.get('token_count', 0)} tokens")
                        
                except Exception as e:
                    print(f"❌ Context search error: {e}")
                
                # Test content extraction
                print("\n4. Testing tavily_extract_content...")
                try:
                    extract_result = await session.call_tool(
                        "tavily_extract_content",
                        {
                            "urls": ["https://www.python.org"]
                        }
                    )
                    
                    if hasattr(extract_result.content[0], 'text'):
                        print(f"Extract result: {extract_result.content[0].text[:200]}...")
                    else:
                        import json
                        result_data = json.loads(str(extract_result.content[0]))
                        if isinstance(result_data, list) and result_data:
                            first_result = result_data[0]
                            print(f"URL: {first_result.get('url', 'N/A')}")
                            print(f"Success: {first_result.get('success', False)}")
                            print(f"Title: {first_result.get('title', 'N/A')[:50]}...")
                        
                except Exception as e:
                    print(f"❌ Content extraction error: {e}")
                    
            else:
                print("\n⚠️  Skipping search tool tests (no API key)")
                print("   To test searches, set TAVILY_API_KEY environment variable")
            
            print("\n" + "=" * 50)
            print("🎉 Tavily MCP Server testing completed!")
            
            if api_key:
                print("✅ All tests completed with API key")
            else:
                print("ℹ️  Basic tests completed (no API key for searches)")


def test_server_import():
    """Test server module import."""
    print("🧪 Testing server import...")
    
    try:
        import tavily_server
        print("✅ Server module imports successfully")
        
        # Check if MCP instance exists
        assert hasattr(tavily_server, 'mcp'), "MCP server instance not found"
        print("✅ MCP server instance created")
        
        # Check server name
        assert tavily_server.mcp.name == "Tavily Internet Search", f"Expected 'Tavily Internet Search', got '{tavily_server.mcp.name}'"
        print(f"✅ Server name: {tavily_server.mcp.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server import failed: {e}")
        return False


async def main():
    """Main test function."""
    print("Tavily Internet MCP Server - Test Suite")
    print("=" * 40)
    
    # Test server import first
    if not test_server_import():
        print("❌ Server import failed, cannot continue")
        return
    
    # Test full functionality
    await test_tavily_server()
    
    print("\n" + "=" * 40)
    print("🚀 Server is ready for use!")
    print("\nNext Steps:")
    print("1. Set TAVILY_API_KEY environment variable")
    print("2. Run: python tavily_server.py")
    print("3. Or use MCP inspector: mcp dev tavily_server.py")


if __name__ == "__main__":
    asyncio.run(main())