#!/usr/bin/env python3
"""
Example usage of the Tavily Internet Search MCP Server.
Demonstrates how to use the server for various search operations.
"""

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def demo_tavily_operations():
    """Demonstrate Tavily search operations using the MCP server."""
    
    # Server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["tavily_server.py"],
        env=os.environ.copy()
    )
    
    print("🚀 Starting Tavily Internet Search MCP Server Demo")
    print("=" * 60)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize the session
            await session.initialize()
            
            print("\n📋 Available Tools:")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  • {tool.name}: {tool.description}")
            
            print("\n📁 Available Resources:")
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"  • {resource.uri}: {resource.name}")
            
            # Example 1: Check API status (without key)
            print("\n📊 Example 1: Checking API status (without key)")
            try:
                status_resource = await session.read_resource("tavily://api-status")
                print(f"API Status: {status_resource.contents[0].text}")
            except Exception as e:
                print(f"Status check failed: {e}")
            
            # Example 2: Get search help
            print("\n📖 Example 2: Getting search help")
            try:
                help_resource = await session.read_resource("tavily://search-help")
                print("Search Help:")
                print(help_resource.contents[0].text[:500] + "...")
            except Exception as e:
                print(f"Help retrieval failed: {e}")
            
            # Example 3: Set API key (mock for demo)
            print("\n🔑 Example 3: Setting API key")
            print("Note: Using mock API key for demonstration")
            print("In real usage, get your API key from https://tavily.com")
            
            try:
                api_key_result = await session.call_tool("tavily_set_api_key", {
                    "api_key": "your_actual_tavily_api_key_here"
                })
                print(f"API Key Result: {api_key_result.content[0].text}")
            except Exception as e:
                print(f"API key setting failed: {e}")
            
            # Example 4: Generate search suggestions
            print("\n💡 Example 4: Generating search suggestions")
            try:
                suggestions_result = await session.call_tool("tavily_get_search_suggestions", {
                    "query": "climate change renewable energy"
                })
                
                if hasattr(suggestions_result.content[0], 'text'):
                    print(f"Suggestions: {suggestions_result.content[0].text}")
                else:
                    import json
                    suggestions_data = json.loads(str(suggestions_result.content[0]))
                    print("Generated Suggestions:")
                    for category, items in suggestions_data.items():
                        print(f"  {category.title().replace('_', ' ')}: {items[:3]}")
                        
            except Exception as e:
                print(f"Suggestions generation failed: {e}")
            
            # Example 5: Test search (will fail without real API key)
            print("\n🔍 Example 5: Testing search functionality")
            print("Note: This will fail without a valid API key")
            
            try:
                search_result = await session.call_tool("tavily_search", {
                    "query": "latest developments in artificial intelligence",
                    "max_results": 5,
                    "include_answer": True
                })
                
                if hasattr(search_result.content[0], 'text'):
                    print(f"Search Result: {search_result.content[0].text}")
                else:
                    import json
                    search_data = json.loads(str(search_result.content[0]))
                    print(f"Query: {search_data.get('query')}")
                    print(f"Answer: {search_data.get('answer', 'No answer provided')}")
                    print(f"Results: {len(search_data.get('results', []))} found")
                    
            except Exception as e:
                expected_errors = ["API key not set", "Authentication", "API request failed"]
                if any(err in str(e) for err in expected_errors):
                    print(f"Expected error (no valid API key): {e}")
                else:
                    print(f"Unexpected error: {e}")
            
            # Example 6: Test content extraction
            print("\n📄 Example 6: Testing content extraction")
            print("Note: This will also fail without a valid API key")
            
            try:
                extract_result = await session.call_tool("tavily_extract_content", {
                    "urls": ["https://example.com", "https://httpbin.org/json"]
                })
                
                if hasattr(extract_result.content[0], 'text'):
                    print(f"Extract Result: {extract_result.content[0].text}")
                else:
                    import json
                    extract_data = json.loads(str(extract_result.content[0]))
                    print("Extraction Results:")
                    for result in extract_data:
                        print(f"  URL: {result.get('url')}")
                        print(f"  Success: {result.get('success')}")
                        if result.get('error'):
                            print(f"  Error: {result.get('error')}")
                            
            except Exception as e:
                expected_errors = ["API key not set", "Authentication", "API request failed"]
                if any(err in str(e) for err in expected_errors):
                    print(f"Expected error (no valid API key): {e}")
                else:
                    print(f"Unexpected error: {e}")
            
            print("\n" + "=" * 60)
            print("🎯 Demo Summary:")
            print("1. ✅ Server initialized successfully")
            print("2. ✅ Tools and resources are available")
            print("3. ✅ Search suggestions work without API key")
            print("4. ⚠️  Search and extraction require valid API key")
            print("\n📋 To use with real searches:")
            print("1. Sign up at https://tavily.com for API key")
            print("2. Use tavily_set_api_key with your real key")
            print("3. Perform searches with tavily_search")
            print("4. Extract content with tavily_extract_content")


async def main():
    """Main demo function."""
    await demo_tavily_operations()


if __name__ == "__main__":
    asyncio.run(main())