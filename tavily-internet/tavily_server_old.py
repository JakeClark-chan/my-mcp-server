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
import json
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from urllib.parse import urlparse

from tavily import TavilyClient
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field


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


class TavilySearchRequest(BaseModel):
    """Tavily search request parameters."""
    query: str = Field(description="Search query")
    search_depth: str = Field(default="basic", description="Search depth: 'basic' or 'advanced'")
    include_answer: bool = Field(default=True, description="Include AI-generated answer")
    include_raw_content: bool = Field(default=False, description="Include raw content from pages")
    max_results: int = Field(default=10, description="Maximum number of results (1-20)")
    include_domains: Optional[List[str]] = Field(default=None, description="Domains to include")
    exclude_domains: Optional[List[str]] = Field(default=None, description="Domains to exclude")
    include_images: bool = Field(default=False, description="Include image results")
    include_image_descriptions: bool = Field(default=False, description="Include image descriptions")


class TavilySearchResult(BaseModel):
    """Individual search result."""
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None


class TavilySearchResponse(BaseModel):
    """Complete search response."""
    query: str
    answer: Optional[str] = None
    results: List[TavilySearchResult]
    images: List[Dict[str, str]] = []
    follow_up_questions: List[str] = []
    response_time: float


class TavilyExtractRequest(BaseModel):
    """Request for content extraction."""
    urls: List[str] = Field(description="URLs to extract content from")


class TavilyExtractResult(BaseModel):
    """Extracted content result."""
    url: str
    content: str
    success: bool
    error: Optional[str] = None


@mcp.tool()
async def tavily_set_api_key(
    api_key: str,
    ctx: Context[ServerSession, TavilyContext] = None
) -> str:
    """
    Set the Tavily API key for authentication.
    
    Args:
        api_key: Your Tavily API key
        
    Returns:
        Confirmation message
    """
    try:
        ctx.request_context.lifespan_context.api_key = api_key
        await ctx.info("Tavily API key set successfully")
        return "✅ Tavily API key has been set successfully"
    except Exception as e:
        await ctx.error(f"Error setting API key: {e}")
        return f"❌ Error setting API key: {e}"


def _get_api_key(ctx: Context[ServerSession, TavilyContext]) -> str:
    """Get the API key or raise an error."""
    api_key = ctx.request_context.lifespan_context.api_key
    if not api_key:
        raise ValueError("Tavily API key not set. Use tavily_set_api_key first.")
    return api_key


@mcp.tool()
async def tavily_search(
    query: str,
    search_depth: str = "basic",
    include_answer: bool = True,
    include_raw_content: bool = False,
    max_results: int = 10,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    include_images: bool = False,
    include_image_descriptions: bool = False,
    ctx: Context[ServerSession, TavilyContext] = None
) -> TavilySearchResponse:
    """
    Search the internet using Tavily API.
    
    Args:
        query: Search query
        search_depth: Search depth - 'basic' or 'advanced'
        include_answer: Include AI-generated answer
        include_raw_content: Include raw content from pages
        max_results: Maximum number of results (1-20)
        include_domains: List of domains to include (optional)
        exclude_domains: List of domains to exclude (optional)
        include_images: Include image results
        include_image_descriptions: Include image descriptions
        
    Returns:
        Search results with answer, results, and metadata
    """
    try:
        api_key = _get_api_key(ctx)
        client = ctx.request_context.lifespan_context.client
        base_url = ctx.request_context.lifespan_context.base_url
        
        # Validate parameters
        if max_results < 1 or max_results > 20:
            raise ValueError("max_results must be between 1 and 20")
            
        if search_depth not in ["basic", "advanced"]:
            raise ValueError("search_depth must be 'basic' or 'advanced'")
        
        # Prepare request payload
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "max_results": max_results,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions
        }
        
        # Add domain filters if provided
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
            
        await ctx.info(f"Searching for: '{query}' with {max_results} results")
        
        # Make API request
        start_time = datetime.now()
        response = await client.post(
            f"{base_url}/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        data = response.json()
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Parse results
        results = []
        for result in data.get("results", []):
            results.append(TavilySearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                published_date=result.get("published_date")
            ))
        
        search_response = TavilySearchResponse(
            query=query,
            answer=data.get("answer"),
            results=results,
            images=data.get("images", []),
            follow_up_questions=data.get("follow_up_questions", []),
            response_time=response_time
        )
        
        await ctx.info(f"Found {len(results)} results in {response_time:.2f}s")
        return search_response
        
    except httpx.HTTPStatusError as e:
        error_msg = f"API request failed: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail.get('error', 'Unknown error')}"
        except:
            pass
        await ctx.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        await ctx.error(f"Search failed: {e}")
        raise


@mcp.tool()
async def tavily_extract_content(
    urls: List[str],
    ctx: Context[ServerSession, TavilyContext] = None
) -> List[TavilyExtractResult]:
    """
    Extract detailed content from specific URLs using Tavily API.
    
    Args:
        urls: List of URLs to extract content from
        
    Returns:
        List of extraction results with content and metadata
    """
    try:
        api_key = _get_api_key(ctx)
        client = ctx.request_context.lifespan_context.client
        base_url = ctx.request_context.lifespan_context.base_url
        
        if not urls:
            raise ValueError("At least one URL must be provided")
            
        if len(urls) > 10:
            raise ValueError("Maximum 10 URLs can be processed at once")
        
        # Validate URLs
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL format: {url}")
        
        payload = {
            "api_key": api_key,
            "urls": urls
        }
        
        await ctx.info(f"Extracting content from {len(urls)} URLs")
        
        # Make API request
        response = await client.post(
            f"{base_url}/extract",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Parse results
        results = []
        for result in data.get("results", []):
            results.append(TavilyExtractResult(
                url=result.get("url", ""),
                content=result.get("content", ""),
                success=result.get("success", False),
                error=result.get("error")
            ))
        
        successful = sum(1 for r in results if r.success)
        await ctx.info(f"Successfully extracted content from {successful}/{len(urls)} URLs")
        
        return results
        
    except httpx.HTTPStatusError as e:
        error_msg = f"API request failed: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail.get('error', 'Unknown error')}"
        except:
            pass
        await ctx.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        await ctx.error(f"Content extraction failed: {e}")
        raise


@mcp.tool()
async def tavily_search_news(
    query: str,
    max_results: int = 10,
    days: int = 7,
    ctx: Context[ServerSession, TavilyContext] = None
) -> TavilySearchResponse:
    """
    Search for recent news using Tavily API.
    
    Args:
        query: News search query
        max_results: Maximum number of results (1-20)
        days: Number of days to look back (1-30)
        
    Returns:
        News search results
    """
    try:
        # Add time constraint to query for recent news
        time_query = f"{query} site:news OR site:reuters OR site:bbc OR site:cnn OR site:ap"
        
        return await tavily_search(
            query=time_query,
            search_depth="advanced",
            include_answer=True,
            max_results=max_results,
            include_domains=[
                "reuters.com", "bbc.com", "cnn.com", "apnews.com", 
                "bloomberg.com", "wsj.com", "nytimes.com", "washingtonpost.com"
            ],
            ctx=ctx
        )
        
    except Exception as e:
        await ctx.error(f"News search failed: {e}")
        raise


@mcp.tool()
async def tavily_search_academic(
    query: str,
    max_results: int = 10,
    ctx: Context[ServerSession, TavilyContext] = None
) -> TavilySearchResponse:
    """
    Search for academic and research content using Tavily API.
    
    Args:
        query: Academic search query
        max_results: Maximum number of results (1-20)
        
    Returns:
        Academic search results
    """
    try:
        # Focus on academic sources
        academic_query = f"{query} filetype:pdf OR site:edu OR site:org OR site:arxiv"
        
        return await tavily_search(
            query=academic_query,
            search_depth="advanced",
            include_answer=True,
            max_results=max_results,
            include_domains=[
                "arxiv.org", "scholar.google.com", "pubmed.ncbi.nlm.nih.gov",
                "ieee.org", "acm.org", "springer.com", "jstor.org"
            ],
            ctx=ctx
        )
        
    except Exception as e:
        await ctx.error(f"Academic search failed: {e}")
        raise


@mcp.tool()
async def tavily_get_search_suggestions(
    query: str,
    ctx: Context[ServerSession, TavilyContext] = None
) -> Dict[str, List[str]]:
    """
    Get search suggestions and related queries.
    
    Args:
        query: Base query to get suggestions for
        
    Returns:
        Dictionary with search suggestions and related terms
    """
    try:
        # Generate variations and suggestions
        suggestions = {
            "related_queries": [],
            "broader_terms": [],
            "narrower_terms": [],
            "alternative_phrasings": []
        }
        
        # Simple suggestion generation (can be enhanced with ML)
        words = query.lower().split()
        
        # Related queries
        suggestions["related_queries"] = [
            f"{query} definition",
            f"{query} examples",
            f"{query} tutorial",
            f"how to {query}",
            f"{query} vs alternatives"
        ]
        
        # Broader terms (remove specific words)
        if len(words) > 1:
            for i in range(len(words)):
                broader = " ".join(words[:i] + words[i+1:])
                if broader and broader not in suggestions["broader_terms"]:
                    suggestions["broader_terms"].append(broader)
        
        # Alternative phrasings
        suggestions["alternative_phrasings"] = [
            f"what is {query}",
            f"{query} explained",
            f"understanding {query}",
            f"{query} guide"
        ]
        
        await ctx.info(f"Generated suggestions for query: '{query}'")
        return suggestions
        
    except Exception as e:
        await ctx.error(f"Error generating suggestions: {e}")
        raise


# Resources for search status and API information
@mcp.resource("tavily://api-status")
async def get_api_status(ctx: Context[ServerSession, TavilyContext] = None) -> str:
    """Get Tavily API connection status."""
    try:
        api_key = ctx.request_context.lifespan_context.api_key
        if api_key:
            # Test API key with a simple request
            client = ctx.request_context.lifespan_context.client
            base_url = ctx.request_context.lifespan_context.base_url
            
            try:
                response = await client.post(
                    f"{base_url}/search",
                    json={"api_key": api_key, "query": "test", "max_results": 1},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return "✅ Tavily API: Connected and authenticated"
                else:
                    return f"⚠️ Tavily API: Authentication issue (status: {response.status_code})"
                    
            except Exception as e:
                return f"❌ Tavily API: Connection failed - {e}"
        else:
            return "⚠️ Tavily API: No API key set. Use tavily_set_api_key first."
            
    except Exception as e:
        return f"❌ API status check failed: {e}"


@mcp.resource("tavily://search-help")
async def get_search_help(ctx: Context[ServerSession, TavilyContext] = None) -> str:
    """Get help information for Tavily search."""
    help_text = """
# Tavily Internet Search Help

## Available Tools:
- **tavily_set_api_key**: Set your Tavily API key
- **tavily_search**: General internet search
- **tavily_extract_content**: Extract content from specific URLs
- **tavily_search_news**: Search recent news
- **tavily_search_academic**: Search academic content
- **tavily_get_search_suggestions**: Get search suggestions

## Search Parameters:
- **query**: Your search terms
- **search_depth**: 'basic' (faster) or 'advanced' (more thorough)
- **max_results**: 1-20 results
- **include_answer**: Get AI-generated answer
- **include_domains/exclude_domains**: Filter by domains

## Tips:
- Use specific keywords for better results
- Try different search depths for varying detail levels
- Use domain filters for targeted searches
- Extract content for detailed analysis of specific pages

## Example Queries:
- "latest AI developments 2024"
- "climate change impact renewable energy"
- "machine learning algorithms comparison"
"""
    return help_text


if __name__ == "__main__":
    mcp.run()