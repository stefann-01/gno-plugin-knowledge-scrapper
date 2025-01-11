from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import Set, Dict, List, Tuple
import os
from pathlib import Path

GBE_URL = "https://gno-by-example.com"

class GBECrawler:
    def __init__(self, base_url: str, max_pages: int = 50, delay: float = 0.5):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.text_content: Dict[str, Dict] = {}  # Store structured content
    
    def extract_code_blocks(self, page) -> List[Tuple[str, str]]:
        """
        Extract code blocks with their filenames
        Returns list of (filename, code_content) tuples
        """
        code_blocks = []
        
        # Get all code tabs
        tabs = page.query_selector_all("button[role='tab'] p")
        for tab in tabs:
            filename = tab.inner_text()
            if not filename.endswith('.gno'):
                continue
                
            # Find the associated code content
            # Using JavaScript to extract the exact text content from Monaco editor
            code_content = page.evaluate("""
                () => {
                    const lines = document.querySelectorAll('.view-line');
                    return Array.from(lines).map(line => {
                        // Get text content without line numbers
                        return line.textContent.trim();
                    }).join('\\n');
                }
            """)
            
            if code_content:
                code_blocks.append((filename, code_content))
        
        return code_blocks

    def extract_page_content(self, page) -> Dict:
        """
        Extract structured content from the page
        """
        # Get the title
        title_elem = page.query_selector("b.chakra-text")
        title = title_elem.inner_text() if title_elem else "Untitled"
        
        # Get the description/explanation text
        description = []
        text_elements = page.query_selector_all("p.chakra-text")
        for elem in text_elements:
            text = elem.inner_text()
            if text and text != title:
                description.append(text)
        
        # Get code blocks
        code_blocks = self.extract_code_blocks(page)
        
        return {
            "title": title,
            "description": "\n".join(description),
            "code_blocks": code_blocks
        }

    def get_navigation_urls(self, page) -> List[str]:
        """Extract URLs in the order they appear in navigation"""
        nav_links = []
        
        # Get all navigation links
        nav_items = page.query_selector_all("a[href^='/tutorials/']")
        for item in nav_items:
            href = item.get_attribute('href')
            if href:
                full_url = urljoin(self.base_url, href)
                nav_links.append(full_url)
        
        return nav_links

    def crawl(self) -> Dict[str, Dict]:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # First get the navigation structure
            print(f"Getting navigation structure from {self.base_url}")
            page.goto(self.base_url, wait_until="networkidle")
            nav_urls = self.get_navigation_urls(page)
            
            ordered_urls = []
            
            # Crawl pages in navigation order
            for url in nav_urls:
                if url in self.visited_urls:
                    continue
                    
                try:
                    print(f"Crawling: {url}")
                    page.goto(url, wait_until="networkidle")
                    
                    # Extract content
                    content = self.extract_page_content(page)
                    if content["code_blocks"]:  # Only store pages with code
                        self.text_content[url] = content
                        ordered_urls.append(url)
                    
                    self.visited_urls.add(url)
                    time.sleep(self.delay)
                    
                except Exception as e:
                    print(f"Error crawling {url}: {str(e)}")
                    continue
            
            browser.close()
            
            # Return content in navigation order
            return {url: self.text_content[url] for url in ordered_urls}

def format_code_block(code: str) -> str:
    """Format code block with proper indentation"""
    lines = code.split('\n')
    # Remove empty lines at start and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines)

def main():
    artifacts_dir = os.path.join(os.path.dirname(__file__), 'artifacts', 'gbe_crawler')
    os.makedirs(artifacts_dir, exist_ok=True)
    
    crawler = GBECrawler(
        base_url=GBE_URL,
        max_pages=50,
        delay=0.5
    )
    
    try:
        print(f"Starting crawl of {GBE_URL}")
        content = crawler.crawl()
        
        # Generate output filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(artifacts_dir, f"gno-by-example.com_{timestamp}.txt")
        
        # Write results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Crawled {len(content)} pages from {GBE_URL}\n")
            f.write("-" * 80 + "\n\n")
            
            for url, page_content in content.items():
                f.write(f"# {page_content['title']}\n")
                f.write(f"URL: {url}\n")
                f.write("-" * 80 + "\n\n")
                
                # Write description
                f.write(page_content['description'] + "\n\n")
                
                # Write code blocks
                for filename, code in page_content['code_blocks']:
                    f.write(f"File: {filename}\n")
                    f.write("```go\n")
                    f.write(format_code_block(code) + "\n")
                    f.write("```\n\n")
                
                f.write("-" * 80 + "\n\n")
        
        print(f"Content has been written to {output_file}")
        print(f"Total pages crawled: {len(content)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
