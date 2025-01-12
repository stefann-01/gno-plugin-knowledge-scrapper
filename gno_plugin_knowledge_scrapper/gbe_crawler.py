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
        
        print("\nExtracting code blocks...")
        
        # Wait for Monaco editor to be present and inject helper function
        page.wait_for_selector('.monaco-editor', state='attached', timeout=5000)
        
        # Inject helper function to get editor content
        page.evaluate("""
            window.getEditorContent = () => {
                const editors = monaco.editor.getEditors();
                return editors.map(editor => editor.getValue());
            }
        """)
        
        # Get all code tabs
        tabs = page.query_selector_all('[role="tab"]')
        filenames = []
        
        # First collect all filenames in order
        for tab in tabs:
            filename_elem = tab.query_selector("p")
            if filename_elem:
                filename = filename_elem.inner_text()
                filenames.append(filename)
        
        print(f"Found {len(filenames)} files")
        
        # Get content from all editors at once
        try:
            contents = page.evaluate("getEditorContent()")
            print(f"Got {len(contents)} editor contents")
            
            # Match filenames with contents
            for filename, content in zip(filenames, contents):
                if content and content.strip():
                    lines = content.splitlines()
                    print(f"✓ Extracted {len(lines)} lines from {filename}")
                    print(f"First few lines: {lines[:2]}")
                    code_blocks.append((filename, content))
                else:
                    print(f"✗ No code content found for {filename}")
        except Exception as e:
            print(f"Error getting editor contents: {str(e)}")
        
        print(f"\nTotal code blocks extracted: {len(code_blocks)}")
        return code_blocks

    def extract_page_content(self, page) -> Dict:
        """
        Extract structured content from the page
        """
        # Get the title
        title_elem = page.query_selector("b.chakra-text")
        title = title_elem.inner_text() if title_elem else "Untitled"
        
        # Get all text and code blocks in order
        content_blocks = []
        
        # Footer lines to exclude (both exact and partial matches)
        footer_exact = {
            "Gno by Example is a community project.",
            "Check out the GitHub repo.",
            "Learn more about Gno.land and",
            "be part of the conversation:",
            "Check out the full example here."
        }
        footer_partial = [
            "Check out the full example",
            "Gno by Example",
            "Check out the GitHub",
            "Learn more about Gno"
        ]
        
        # Get all content elements in order
        elements = page.query_selector_all("p.chakra-text, [role='tab']")
        current_text = []
        
        # Keep track of filenames to skip them in text
        filenames = set()
        
        # First collect all filenames
        for elem in elements:
            if elem.get_attribute('role') == 'tab':
                filename = elem.query_selector("p").inner_text()
                filenames.add(filename)
        
        # Now process elements
        for elem in elements:
            if elem.get_attribute('role') == 'tab':
                # If we have accumulated text, add it as a block
                if current_text:
                    # Filter out lines that are just filenames
                    filtered_text = [line for line in current_text if line not in filenames]
                    if filtered_text:
                        content_blocks.append(('text', '\n'.join(filtered_text)))
                    current_text = []
                # Add the code block marker
                filename = elem.query_selector("p").inner_text()
                content_blocks.append(('code', filename))
            else:
                # Get text with links preserved
                text = self.extract_text_with_links(elem)
                if not text:
                    continue
                    
                # Skip empty, title, and footer lines
                if text == title or text in footer_exact:
                    continue
                # Skip lines containing footer content
                if any(footer in text for footer in footer_partial):
                    continue
                current_text.append(text)
        
        # Add any remaining text
        if current_text:
            # Filter out lines that are just filenames
            filtered_text = [line for line in current_text if line not in filenames]
            if filtered_text:
                content_blocks.append(('text', '\n'.join(filtered_text)))
        
        # Get code contents
        code_contents = {}
        try:
            # Wait for Monaco editor to be present and inject helper function
            page.wait_for_selector('.monaco-editor', state='attached', timeout=5000)
            
            # Inject helper function to get editor content
            page.evaluate("""
                window.getEditorContent = () => {
                    const editors = monaco.editor.getEditors();
                    return editors.map(editor => editor.getValue());
                }
            """)
            
            # Get all code tabs for filenames
            tabs = page.query_selector_all('[role="tab"]')
            filenames = []
            for tab in tabs:
                filename_elem = tab.query_selector("p")
                if filename_elem:
                    filenames.append(filename_elem.inner_text())
            
            # Get content from all editors at once
            contents = page.evaluate("getEditorContent()")
            
            # Match filenames with contents
            for filename, content in zip(filenames, contents):
                if content and content.strip():
                    code_contents[filename] = content.strip()
        except Exception as e:
            print(f"Error getting editor contents: {str(e)}")
        
        return {
            "title": title,
            "content_blocks": content_blocks,
            "code_contents": code_contents
        }
        
    def extract_text_with_links(self, elem) -> str:
        """Extract text content preserving links in markdown format"""
        # First check if the element itself is empty
        text = elem.inner_text().strip()
        if not text:
            return ""
            
        # Get all links in the element
        links = elem.query_selector_all("a")
        if not links:
            return text
            
        # Get the HTML content to preserve link positions
        html = elem.inner_html()
        
        # For each link, replace it with markdown format
        for link in links:
            link_text = link.inner_text()
            href = link.get_attribute("href")
            if href and link_text:
                # Create markdown link
                markdown_link = f"[{link_text}]({href})"
                # Replace in HTML (using a unique placeholder to avoid nested replacements)
                html = html.replace(str(link.evaluate("node => node.outerHTML")), markdown_link)
        
        # Convert any remaining HTML to plain text (remove tags)
        text = BeautifulSoup(html, 'html.parser').get_text()
        return text.strip()

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
                    if content["code_contents"]:  # Only store pages with code
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
                
                # Write content blocks in order
                for block_type, block_content in page_content['content_blocks']:
                    if block_type == 'text':
                        f.write(block_content + "\n\n")
                    else:  # code block
                        filename = block_content
                        if filename in page_content['code_contents']:
                            f.write(f"File: {filename}\n")
                            f.write("```\n")
                            f.write(format_code_block(page_content['code_contents'][filename]) + "\n")
                            f.write("```\n\n")
                
                f.write("-" * 80 + "\n\n")
        
        print(f"Content has been written to {output_file}")
        print(f"Total pages crawled: {len(content)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
