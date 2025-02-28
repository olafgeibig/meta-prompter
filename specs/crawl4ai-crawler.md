# Key Crawl4AI Features for Domain-Limited Crawling

Based on the Crawl4AI documentation, here are the essential components to implement a crawler with domain, path, and pattern restrictions that outputs content as markdown.

## 1. Basic Setup

```python
import asyncio
import re
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    browser_config = BrowserConfig(
        headless=True,  # Run browser invisibly
        verbose=True    # Enable detailed logging
    )
    
    # Starting URL - this defines your initial path
    start_url = "https://example.com/docs/"
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Main crawl configuration
        config = CrawlerRunConfig(
            exclude_external_links=True,  # Stay within same domain
            exclude_social_media_links=True,
            word_count_threshold=10,      # Filter out short text snippets
            cache_mode=CacheMode.ENABLED  # Enable caching for efficiency
        )
        
        # Initial crawl at starting URL
        result = await crawler.arun(url=start_url, config=config)
        
        # Process results...
```

## 2. Domain and Path Restriction

There are multiple ways to restrict crawling by domain and path:

### Method 1: Direct Restriction

```python
config = CrawlerRunConfig(
    # Stay within the same domain
    exclude_external_links=True,
    
    # Block specific domains if needed
    exclude_domains=["ads.example.com", "otherdomain.com"],
    
    # Use CSS selector to focus only on main content
    css_selector="main.content"
)
```

### Method 2: Custom URL Filtering with Pattern Matching

```python
async def crawl_with_path_restriction(start_url, path_pattern=None, max_pages=10):
    base_domain = urlparse(start_url).netloc
    crawled_urls = set()
    to_crawl = [start_url]
    results = []
    
    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            exclude_external_links=True,
            cache_mode=CacheMode.ENABLED
        )
        
        while to_crawl and len(crawled_urls) < max_pages:
            current_url = to_crawl.pop(0)
            if current_url in crawled_urls:
                continue
                
            # Crawl the current URL
            result = await crawler.arun(url=current_url, config=config)
            if not result.success:
                continue
                
            # Store the result
            crawled_urls.add(current_url)
            results.append(result)
            
            # Extract internal links from the result
            internal_links = result.links.get("internal", [])
            for link in internal_links:
                url = link.get("href")
                if not url:
                    continue
                    
                # Check if URL matches domain and path pattern
                parsed = urlparse(url)
                if parsed.netloc != base_domain:
                    continue
                    
                # Check path pattern if provided
                if path_pattern and not re.match(path_pattern, parsed.path):
                    continue
                    
                # Add URL to crawl queue if not already crawled
                if url not in crawled_urls and url not in to_crawl:
                    to_crawl.append(url)
                    
        return results
```

## 3. Markdown Output Options

Crawl4AI automatically generates markdown for each page. You can customize the markdown generation:

```python
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

# Create a markdown generator with content filtering
md_generator = DefaultMarkdownGenerator(
    # Filter out low-quality content
    content_filter=PruningContentFilter(
        threshold=0.45,
        threshold_type="dynamic",
        min_word_threshold=5
    ),
    # Configuration options
    options={
        "ignore_links": False,  # Keep links in markdown
        "ignore_images": False, # Keep images in markdown
        "body_width": 80        # Wrap text at 80 characters
    }
)

config = CrawlerRunConfig(
    markdown_generator=md_generator,
    # Other config options...
)
```

## 4. Putting It All Together

Here's a complete implementation that:
1. Crawls within a specific domain
2. Limits to URLs matching a path pattern
3. Outputs clean markdown

```python
import asyncio
import re
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

async def crawl_site(start_url, path_pattern=None, max_pages=10):
    """
    Crawl a website with domain and path restrictions
    
    Args:
        start_url: The starting URL (defines the domain)
        path_pattern: Regex pattern for URL paths to follow (e.g., '/docs/.*')
        max_pages: Maximum number of pages to crawl
        
    Returns:
        Dictionary mapping URLs to their markdown content
    """
    base_domain = urlparse(start_url).netloc
    crawled_urls = set()
    to_crawl = [start_url]
    results = {}
    
    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    # Configure markdown generation
    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.45),
        options={"body_width": 80}
    )
    
    # Create crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        config = CrawlerRunConfig(
            exclude_external_links=True,
            markdown_generator=md_generator,
            cache_mode=CacheMode.ENABLED
        )
        
        while to_crawl and len(crawled_urls) < max_pages:
            current_url = to_crawl.pop(0)
            if current_url in crawled_urls:
                continue
            
            print(f"Crawling: {current_url}")
            result = await crawler.arun(url=current_url, config=config)
            
            if not result.success:
                print(f"Failed to crawl {current_url}: {result.error_message}")
                continue
                
            # Store the markdown result
            crawled_urls.add(current_url)
            
            # Use the fit_markdown if available, otherwise use raw_markdown
            if result.markdown_v2 and result.markdown_v2.fit_markdown:
                markdown = result.markdown_v2.fit_markdown
            elif result.markdown_v2:
                markdown = result.markdown_v2.raw_markdown
            else:
                markdown = result.markdown
                
            results[current_url] = markdown
            
            # Find new URLs to crawl
            internal_links = result.links.get("internal", [])
            for link in internal_links:
                url = link.get("href")
                if not url:
                    continue
                    
                # Check domain and path pattern
                parsed = urlparse(url)
                if parsed.netloc != base_domain:
                    continue
                    
                if path_pattern and not re.match(path_pattern, parsed.path):
                    continue
                    
                if url not in crawled_urls and url not in to_crawl:
                    to_crawl.append(url)
    
    return results

async def main():
    # Example usage:
    start_url = "https://docs.example.com/"
    
    # Limit to URLs in the /docs/ section
    path_pattern = r"/docs/.*"
    
    # Run the crawler
    markdown_content = await crawl_site(
        start_url=start_url,
        path_pattern=path_pattern,
        max_pages=20
    )
    
    # Save results to files
    for url, markdown in markdown_content.items():
        # Create a filename from the URL
        filename = urlparse(url).path.replace('/', '_') or "index"
        if not filename.endswith('.md'):
            filename += '.md'
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# {url}\n\n")
            f.write(markdown)
            
        print(f"Saved: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Key Configuration Options

Here are the most relevant configuration parameters for domain/path-limited crawling:

| Parameter | Description |
|-----------|-------------|
| `exclude_external_links` | Set to `True` to stay within the same domain |
| `exclude_domains` | List of domains to explicitly block |
| `css_selector` | Limits content to specific parts of the page |
| `excluded_tags` | Removes specific HTML elements |
| `word_count_threshold` | Filters out content blocks with few words |
| `cache_mode` | Controls caching behavior for faster repeat crawls |

With this setup, you can create a focused crawler that stays within specified domain and path constraints while generating clean markdown output for each page.