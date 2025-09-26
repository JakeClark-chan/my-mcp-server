#!/usr/bin/env python3
"""
MCP Server for Tavily Internet Search.

Provides comprehensive internet search functionality including:
- Search web content with various filters and options
- Extract detailed content from URLs
- Handle different search types (general, news, academic, etc.)
- Support for advanced search parameters
"""

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from tavily import TavilyClient
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field

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


@dataclass
class TavilyContext:
    """Application context for Tavily operations."""
    api_key: Optional[str]
    client: Optional[TavilyClient]


@asynccontextmanager
async def tavily_lifespan(server: FastMCP) -> AsyncIterator[TavilyContext]:
    """Manage Tavily client lifecycle."""
    api_key = os.getenv('TAVILY_API_KEY')
    client = None
    
    if api_key:
        client = TavilyClient(api_key=api_key)
    
    try:
        yield TavilyContext(api_key=api_key, client=client)
    finally:
        # TavilyClient doesn't need explicit cleanup
        pass


# Initialize the MCP server
mcp = FastMCP("Tavily Internet Search", lifespan=tavily_lifespan)


class TavilySearchItem(BaseModel):
    """Individual search result item."""
    title: str = Field(description="Title of the result")
    url: str = Field(description="URL of the result")
    content: str = Field(description="Content snippet")
    raw_content: Optional[str] = Field(default=None, description="Raw HTML content")
    score: float = Field(description="Relevance score")
    published_date: Optional[str] = Field(default=None, description="Published date")


class TavilyImage(BaseModel):
    """Image search result."""
    url: str = Field(description="Image URL")
    description: str = Field(description="Image description")


class TavilySearchResult(BaseModel):
    """Complete search results."""
    query: str = Field(description="Original search query")
    answer: str = Field(description="AI-generated answer")
    results: List[TavilySearchItem] = Field(description="Search results")
    images: List[TavilyImage] = Field(default_factory=list, description="Image results")
    search_depth: str = Field(description="Search depth used")
    topic: str = Field(description="Search topic")
    response_time: float = Field(description="Response time in seconds")
    total_results: int = Field(description="Total number of results")


class TavilyExtractItem(BaseModel):
    """Extracted content from a URL."""
    url: str = Field(description="Source URL")
    title: str = Field(description="Page title")
    content: str = Field(description="Extracted content")
    author: Optional[str] = Field(default=None, description="Content author")
    published_date: Optional[str] = Field(default=None, description="Published date")
    language: Optional[str] = Field(default=None, description="Content language")
    success: bool = Field(description="Whether extraction was successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")


def _get_tavily_client(ctx: Context[ServerSession, TavilyContext]) -> TavilyClient:
    """Get the Tavily client or raise an error."""
    if not ctx.request_context.lifespan_context.api_key:
        raise ValueError("Tavily API key not found. Please set TAVILY_API_KEY environment variable.")
    
    if not ctx.request_context.lifespan_context.client:
        raise ValueError("Tavily client not initialized")
    
    return ctx.request_context.lifespan_context.client


@mcp.tool()
async def tavily_search(
    query: str,
    search_depth: str = "basic",
    topic: str = "general",
    days: Optional[int] = None,
    max_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_images: bool = False,
    ctx: Context[ServerSession, TavilyContext] = None
) -> TavilySearchResult:
    """
    Search the internet using Tavily AI search engine.
    
    Args:
        query: Search query string
        search_depth: Search depth ("basic" or "advanced")
        topic: Search topic ("general", "news", or "finance")
        days: Number of days to look back (for news/recent content)
        max_results: Maximum number of results to return (1-20)
        include_domains: List of domains to include in search
        exclude_domains: List of domains to exclude from search
        include_answer: Include AI-generated answer
        include_raw_content: Include raw HTML content
        include_images: Include images in results
        
    Returns:
        Search results with answer, sources, and metadata
    """
    try:
        client = _get_tavily_client(ctx)
        
        # Validate parameters
        if search_depth not in ["basic", "advanced"]:
            search_depth = "basic"
            
        if topic not in ["general", "news", "finance"]:
            topic = "general"
            
        if max_results < 1 or max_results > 20:
            max_results = 5
            
        await ctx.info(f"Searching Tavily for: {query}")
        
        # Prepare search parameters
        search_params = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images
        }
        
        # Add optional parameters
        if days is not None:
            search_params["days"] = days
            
        if include_domains:
            search_params["include_domains"] = include_domains
            
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains
        
        # Record start time for response measurement
        start_time = datetime.now()
        
        # Make search request using Tavily client
        data = client.search(**search_params)
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Parse results
        results = []
        for item in data.get("results", []):
            result = TavilySearchItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                raw_content=item.get("raw_content"),
                score=item.get("score", 0.0),
                published_date=item.get("published_date")
            )
            results.append(result)
        
        # Parse images if included
        images = []
        for img in data.get("images", []):
            image = TavilyImage(
                url=img.get("url", ""),
                description=img.get("description", "")
            )
            images.append(image)
        
        search_result = TavilySearchResult(
            query=query,
            answer=data.get("answer", ""),
            results=results,
            images=images,
            search_depth=search_depth,
            topic=topic,
            response_time=response_time,
            total_results=len(results)
        )
        
        await ctx.info(f"Found {len(results)} results in {response_time:.2f}s")
        return search_result
        
    except Exception as e:
        error_msg = f"Search failed: {e}"
        await ctx.error(error_msg)
        raise ValueError(error_msg)


@mcp.tool()
async def tavily_extract_content(
    urls: List[str],
    ctx: Context[ServerSession, TavilyContext] = None
) -> List[TavilyExtractItem]:
    """
    Extract detailed content from specific URLs using Tavily API.
    
    Args:
        urls: List of URLs to extract content from
        
    Returns:
        List of extracted content for each URL
    """
    try:
        client = _get_tavily_client(ctx)
        
        if not urls:
            raise ValueError("No URLs provided for content extraction")
            
        if len(urls) > 10:
            await ctx.warning(f"Too many URLs ({len(urls)}). Processing first 10 only.")
            urls = urls[:10]
            
        await ctx.info(f"Extracting content from {len(urls)} URL(s)")
        
        results = []
        
        for url in urls:
            try:
                # Extract content using Tavily client
                data = client.extract(urls=[url])
                
                if data and "results" in data and data["results"]:
                    result_data = data["results"][0]
                    
                    extract_result = TavilyExtractItem(
                        url=url,
                        title=result_data.get("title", ""),
                        content=result_data.get("content", ""),
                        author=result_data.get("author"),
                        published_date=result_data.get("published_date"),
                        language=result_data.get("language"),
                        success=True
                    )
                else:
                    extract_result = TavilyExtractItem(
                        url=url,
                        title="",
                        content="",
                        success=False,
                        error="No content extracted"
                    )
                    
                results.append(extract_result)
                
            except Exception as e:
                await ctx.warning(f"Failed to extract content from {url}: {e}")
                error_result = TavilyExtractItem(
                    url=url,
                    title="",
                    content="",
                    success=False,
                    error=str(e)
                )
                results.append(error_result)
        
        successful_extractions = sum(1 for r in results if r.success)
        await ctx.info(f"Successfully extracted content from {successful_extractions}/{len(urls)} URLs")
        
        return results
        
    except Exception as e:
        error_msg = f"Content extraction failed: {e}"
        await ctx.error(error_msg)
        raise ValueError(error_msg)


@mcp.tool()
async def tavily_get_search_context(
    query: str,
    max_tokens: int = 4000,
    search_depth: str = "basic",
    topic: str = "general",
    days: Optional[int] = None,
    ctx: Context[ServerSession, TavilyContext] = None
) -> Dict[str, Union[str, int]]:
    """
    Get search context optimized for RAG (Retrieval Augmented Generation).
    This returns a condensed context suitable for feeding to language models.
    
    Args:
        query: Search query string
        max_tokens: Maximum tokens in the context (approximate)
        search_depth: Search depth ("basic" or "advanced")
        topic: Search topic ("general", "news", or "finance")
        days: Number of days to look back
        
    Returns:
        Dictionary with context and metadata
    """
    try:
        client = _get_tavily_client(ctx)
        
        await ctx.info(f"Getting search context for: {query}")
        
        # Prepare search parameters
        search_params = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_tokens": max_tokens
        }
        
        if days is not None:
            search_params["days"] = days
        
        # Get context using Tavily client
        data = client.get_search_context(**search_params)
        
        result = {
            "query": query,
            "context": data,
            "max_tokens": max_tokens,
            "search_depth": search_depth,
            "topic": topic,
            "token_count": len(data.split()) if isinstance(data, str) else 0
        }
        
        await ctx.info(f"Generated context with ~{result['token_count']} tokens")
        return result
        
    except Exception as e:
        error_msg = f"Context generation failed: {e}"
        await ctx.error(error_msg)
        raise ValueError(error_msg)


@mcp.tool()
async def tavily_qna_search(
    query: str,
    search_depth: str = "advanced",
    topic: str = "general",
    days: Optional[int] = None,
    max_results: int = 5,
    ctx: Context[ServerSession, TavilyContext] = None
) -> Dict[str, Union[str, List[str]]]:
    """
    Perform a Q&A focused search that returns a direct answer with sources.
    Optimized for question-answering scenarios.
    
    Args:
        query: Question or search query
        search_depth: Search depth ("basic" or "advanced")
        topic: Search topic ("general", "news", or "finance")
        days: Number of days to look back
        max_results: Maximum number of supporting sources
        
    Returns:
        Dictionary with answer, sources, and follow-up questions
    """
    try:
        client = _get_tavily_client(ctx)
        
        await ctx.info(f"Performing Q&A search for: {query}")
        
        # Prepare search parameters optimized for Q&A
        search_params = {
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results
        }
        
        if days is not None:
            search_params["days"] = days
        
        # Perform Q&A search (returns string directly)
        answer = client.qna_search(**search_params)
        
        # Also get regular search results for sources
        search_data = client.search(query=query, search_depth=search_depth, topic=topic, max_results=max_results, include_answer=False)
        
        result = {
            "query": query,
            "answer": answer,
            "sources": [item.get("url", "") for item in search_data.get("results", [])],
            "source_titles": [item.get("title", "") for item in search_data.get("results", [])],
            "follow_up_questions": [],  # qna_search doesn't provide follow-up questions
            "search_depth": search_depth,
            "topic": topic
        }
        
        await ctx.info(f"Generated answer with {len(result['sources'])} sources")
        return result
        
    except Exception as e:
        error_msg = f"Q&A search failed: {e}"
        await ctx.error(error_msg)
        raise ValueError(error_msg)


# Resources for API status and configuration
@mcp.resource("tavily://status")
def get_tavily_status() -> str:
    """Get Tavily API connection status."""
    try:
        # Get API key from environment (already loaded at startup)
        api_key = os.environ.get("TAVILY_API_KEY")
        
        if not api_key:
            return "❌ Tavily API Status: No API key configured\nSet TAVILY_API_KEY environment variable"
        
        # Create a test client
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        
        # Test the connection with a simple search
        test_result = client.search(query="test", max_results=1)
        return f"✅ Tavily API Status: Connected and working\nAPI Key: {api_key[:8]}...{api_key[-4:]}"
    except Exception as e:
        return f"❌ Tavily API Status: Connection failed\nError: {e}"


@mcp.resource("tavily://usage")
def get_tavily_usage_info() -> str:
    """Get Tavily API usage information and limits."""
    return """📊 Tavily API Usage Information:

Search Limits:
• Max results per search: 20
• Max URLs for extraction: 10
• Max tokens for context: 4000+

Search Types:
• Basic: Fast, essential results
• Advanced: Comprehensive, detailed results

Topics:
• General: All-purpose search
• News: Recent news and events  
• Finance: Financial and business content

Rate Limits:
• Depends on your Tavily plan
• Free tier: Limited requests per month
• Paid plans: Higher limits

Best Practices:
• Use 'basic' depth for quick searches
• Use 'advanced' depth for comprehensive research
• Specify topics for better relevance
• Use 'days' parameter for recent content
"""


if __name__ == "__main__":
    mcp.run()