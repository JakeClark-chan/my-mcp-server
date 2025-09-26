# Tavily Internet Search MCP Server

A comprehensive Model Context Protocol (MCP) server for internet searching using the Tavily API. Provides powerful search capabilities, content extraction, and specialized search functions for news and academic content.

## Features

### Core Search Functionality
- **General Internet Search** with customizable parameters
- **Content Extraction** from specific URLs
- **AI-Generated Answers** for search queries
- **Advanced Search Depth** options (basic/advanced)
- **Domain Filtering** (include/exclude specific domains)
- **Image Search** with descriptions

### Specialized Search Types
- **News Search** - Recent news from major sources
- **Academic Search** - Research papers and academic content
- **Search Suggestions** - Related queries and alternative phrasings

### Advanced Features
- **Multiple Result Formats** - Raw content, summaries, metadata
- **Response Time Tracking** - Performance monitoring
- **Error Handling** - Comprehensive error messages and fallbacks
- **Resource Monitoring** - API status checking

## Installation

1. Install dependencies:
```bash
pip install "mcp[cli]" httpx pydantic
```

2. Get a Tavily API key from [tavily.com](https://tavily.com)

## Usage

### Running the Server

```bash
# Direct execution
python tavily_server.py

# Or with MCP tools
mcp dev tavily_server.py
```

### Available Tools

#### Authentication
- `tavily_set_api_key` - Set your Tavily API key

#### Search Operations
- `tavily_search` - General internet search with full customization
- `tavily_search_news` - Search recent news from major sources  
- `tavily_search_academic` - Search academic and research content
- `tavily_extract_content` - Extract detailed content from URLs
- `tavily_get_search_suggestions` - Generate related search queries

### Available Resources

- `tavily://api-status` - Check API connection and authentication status
- `tavily://search-help` - Detailed help and usage examples

## Examples

### Basic Search
```python
# Set API key first
await session.call_tool("tavily_set_api_key", {
    "api_key": "your_tavily_api_key"
})

# Perform a search
search_result = await session.call_tool("tavily_search", {
    "query": "latest AI developments 2024",
    "max_results": 10,
    "include_answer": True,
    "search_depth": "advanced"
})
```

### Content Extraction
```python
# Extract content from specific URLs
extract_result = await session.call_tool("tavily_extract_content", {
    "urls": [
        "https://example.com/article1",
        "https://example.com/article2"
    ]
})
```

### News Search
```python
# Search recent news
news_result = await session.call_tool("tavily_search_news", {
    "query": "renewable energy breakthrough",
    "max_results": 5,
    "days": 7
})
```

### Academic Search
```python
# Search academic content
academic_result = await session.call_tool("tavily_search_academic", {
    "query": "machine learning algorithms",
    "max_results": 10
})
```

### Advanced Search with Filters
```python
# Search with domain filtering
filtered_search = await session.call_tool("tavily_search", {
    "query": "climate change data",
    "include_domains": ["nature.com", "science.org", "nasa.gov"],
    "exclude_domains": ["social-media-sites.com"],
    "max_results": 15,
    "include_raw_content": True
})
```

### Search Suggestions
```python
# Get related search queries
suggestions = await session.call_tool("tavily_get_search_suggestions", {
    "query": "artificial intelligence"
})
```

## Response Formats

### Search Response
```json
{
  "query": "your search query",
  "answer": "AI-generated answer to your query",
  "results": [
    {
      "title": "Article Title",
      "url": "https://example.com/article",
      "content": "Article summary...",
      "score": 0.95,
      "published_date": "2024-01-15"
    }
  ],
  "images": [],
  "follow_up_questions": ["Related question 1", "Related question 2"],
  "response_time": 1.23
}
```

### Content Extraction Response
```json
[
  {
    "url": "https://example.com/page",
    "content": "Full extracted content...",
    "success": true,
    "error": null
  }
]
```

## Configuration Options

### Search Parameters
- **query**: Search terms (required)
- **search_depth**: "basic" (faster) or "advanced" (more thorough)
- **max_results**: 1-20 results per search
- **include_answer**: Include AI-generated answer
- **include_raw_content**: Include full page content
- **include_domains**: List of domains to focus on
- **exclude_domains**: List of domains to avoid
- **include_images**: Include image results
- **include_image_descriptions**: Include image descriptions

### Performance Tuning
- Use "basic" search depth for faster results
- Limit max_results for quicker responses
- Use domain filtering to improve relevance
- Enable raw content only when needed

## Error Handling

The server provides comprehensive error handling for:
- **Authentication errors** - Invalid or missing API keys
- **Rate limiting** - API quota exceeded
- **Network issues** - Connection timeouts and failures
- **Invalid parameters** - Malformed requests
- **Content extraction failures** - Inaccessible URLs

## Testing

Run the test suite:
```bash
python test_tavily_server.py
```

Run the demo:
```bash
python demo_tavily.py
```

## API Limits

Tavily API has usage limits based on your subscription:
- Free tier: Limited searches per month
- Paid tiers: Higher limits and additional features
- Rate limiting: Requests per minute restrictions

Check your usage at [tavily.com/dashboard](https://tavily.com/dashboard)

## Security Considerations

- **API Key Security** - Store keys securely, never commit to version control
- **Content Filtering** - Be aware of potentially sensitive content in results
- **Rate Limiting** - Implement appropriate delays for bulk operations
- **Error Logging** - Monitor for unusual API errors or access patterns

## Troubleshooting

### Common Issues

1. **"API key not set"** - Use `tavily_set_api_key` first
2. **Authentication failed** - Check API key validity
3. **Rate limit exceeded** - Wait and retry, or upgrade plan
4. **No results found** - Try different search terms or broader queries
5. **Content extraction failed** - Some sites block automated access

### Debug Mode

Enable detailed logging by setting environment variable:
```bash
export TAVILY_DEBUG=true
python tavily_server.py
```

## Requirements

- Python 3.8+
- MCP Python SDK
- httpx (HTTP client)
- pydantic (data validation)
- Valid Tavily API key

## License

This project follows the same licensing terms as the MCP ecosystem.