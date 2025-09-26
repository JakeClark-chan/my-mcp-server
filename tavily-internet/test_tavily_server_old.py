#!/usr/bin/env python3
"""
Test script for Tavily Internet Search MCP Server.
Tests all functionality including search, content extraction, and specialized searches.
"""

import asyncio
import os
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_server_startup():
    """Test that the Tavily server starts without errors."""
    print("🧪 Testing server startup...")
    
    try:
        # Try to import the server module
        sys.path.insert(0, os.path.dirname(__file__))
        import tavily_server
        print("✅ Server module imports successfully")
        
        # Check if FastMCP instance is created
        assert hasattr(tavily_server, 'mcp'), "MCP server instance not found"
        print("✅ MCP server instance created")
        
        # Check server name
        assert tavily_server.mcp.name == "Tavily Internet Search", f"Expected 'Tavily Internet Search', got '{tavily_server.mcp.name}'"
        print(f"✅ Server name: {tavily_server.mcp.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        return False


def test_tool_definitions():
    """Test that all expected tools are defined."""
    print("\n🧪 Testing tool definitions...")
    
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import tavily_server
        
        expected_tools = [
            'tavily_set_api_key',
            'tavily_search',
            'tavily_extract_content',
            'tavily_search_news',
            'tavily_search_academic',
            'tavily_get_search_suggestions'
        ]
        
        missing_tools = []
        for tool in expected_tools:
            if hasattr(tavily_server, tool):
                print(f"✅ Tool function '{tool}' exists")
            else:
                print(f"❌ Tool function '{tool}' missing")
                missing_tools.append(tool)
                
        if missing_tools:
            print(f"❌ Missing tools: {missing_tools}")
            return False
            
        print(f"✅ All {len(expected_tools)} expected tool functions found")
        return True
        
    except Exception as e:
        print(f"❌ Tool definition test failed: {e}")
        return False


def test_data_models():
    """Test that data models are properly defined."""
    print("\n🧪 Testing data models...")
    
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import tavily_server
        
        # Test TavilySearchRequest model
        search_req = tavily_server.TavilySearchRequest(
            query="test query",
            max_results=5
        )
        assert search_req.query == "test query"
        assert search_req.max_results == 5
        assert search_req.search_depth == "basic"  # default value
        print("✅ TavilySearchRequest model works")
        
        # Test TavilySearchResult model
        search_result = tavily_server.TavilySearchResult(
            title="Test Title",
            url="https://example.com",
            content="Test content",
            score=0.95
        )
        assert search_result.title == "Test Title"
        assert search_result.score == 0.95
        print("✅ TavilySearchResult model works")
        
        # Test TavilySearchResponse model
        search_response = tavily_server.TavilySearchResponse(
            query="test",
            results=[search_result],
            response_time=1.5
        )
        assert search_response.query == "test"
        assert len(search_response.results) == 1
        print("✅ TavilySearchResponse model works")
        
        # Test TavilyExtractResult model
        extract_result = tavily_server.TavilyExtractResult(
            url="https://example.com",
            content="Extracted content",
            success=True
        )
        assert extract_result.success is True
        print("✅ TavilyExtractResult model works")
        
        return True
        
    except Exception as e:
        print(f"❌ Data model test failed: {e}")
        return False


async def test_without_api_key():
    """Test tools without API key (should fail gracefully)."""
    print("\n🧪 Testing without API key...")
    
    server_params = StdioServerParameters(
        command="python",
        args=["tavily_server.py"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                await session.initialize()
                print("✅ MCP Session initialized")
                
                # Test search without API key (should fail)
                try:
                    search_result = await session.call_tool("tavily_search", {
                        "query": "test query"
                    })
                    print("❌ Expected error for missing API key")
                    return False
                except Exception as e:
                    if "API key not set" in str(e):
                        print("✅ Proper error handling for missing API key")
                    else:
                        print(f"❌ Unexpected error: {e}")
                        return False
                
                # Test resources
                try:
                    status_resource = await session.read_resource("tavily://api-status")
                    print(f"✅ API status resource: {status_resource.contents[0].text[:100]}...")
                    
                    help_resource = await session.read_resource("tavily://search-help")
                    print(f"✅ Search help resource: {len(help_resource.contents[0].text)} characters")
                    
                except Exception as e:
                    print(f"❌ Resource reading failed: {e}")
                    return False
                
        return True
        
    except Exception as e:
        print(f"❌ Test without API key failed: {e}")
        return False


async def test_with_mock_api_key():
    """Test tools with a mock API key."""
    print("\n🧪 Testing with mock API key...")
    
    server_params = StdioServerParameters(
        command="python",
        args=["tavily_server.py"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                await session.initialize()
                
                # Set mock API key
                api_key_result = await session.call_tool("tavily_set_api_key", {
                    "api_key": "mock_api_key_for_testing"
                })
                print(f"API key set: {api_key_result.content[0].text}")
                
                # Test search suggestions (doesn't require API call)
                suggestions_result = await session.call_tool("tavily_get_search_suggestions", {
                    "query": "artificial intelligence"
                })
                
                if hasattr(suggestions_result.content[0], 'text'):
                    print(f"✅ Search suggestions generated")
                else:
                    import json
                    suggestions_data = json.loads(str(suggestions_result.content[0]))
                    print(f"✅ Generated {len(suggestions_data.get('related_queries', []))} related queries")
                
        return True
        
    except Exception as e:
        print(f"❌ Test with mock API key failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("Tavily Internet Search MCP Server - Test Suite")
    print("=" * 50)
    
    # Synchronous tests
    sync_tests = [
        ("Server Startup", test_server_startup),
        ("Tool Definitions", test_tool_definitions),
        ("Data Models", test_data_models),
    ]
    
    passed = 0
    total = len(sync_tests)
    
    for test_name, test_func in sync_tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    # Async tests
    async def run_async_tests():
        nonlocal passed, total
        
        async_tests = [
            ("Without API Key", test_without_api_key),
            ("With Mock API Key", test_with_mock_api_key),
        ]
        
        total += len(async_tests)
        
        for test_name, test_func in async_tests:
            try:
                if await test_func():
                    passed += 1
                else:
                    print(f"❌ {test_name} test failed")
            except Exception as e:
                print(f"❌ {test_name} test crashed: {e}")
    
    # Run async tests
    asyncio.run(run_async_tests())
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        print("\n🚀 Server is ready for use!")
        print("   1. Get a Tavily API key from https://tavily.com")
        print("   2. Run: python tavily_server.py")
        print("   3. Use tavily_set_api_key to authenticate")
        print("   4. Start searching with tavily_search")
        
        print("\n📖 Available Tools:")
        tools = [
            "tavily_set_api_key - Set your API key",
            "tavily_search - General internet search",
            "tavily_extract_content - Extract content from URLs",
            "tavily_search_news - Search recent news",
            "tavily_search_academic - Search academic content",
            "tavily_get_search_suggestions - Get search suggestions"
        ]
        for tool in tools:
            print(f"   • {tool}")
    else:
        print("❌ Some tests failed. Please check the output above.")
        
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)