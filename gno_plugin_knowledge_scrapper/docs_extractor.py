from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import sys
from pathlib import Path
import time
import requests
import base64
from urllib.parse import urlparse
from dotenv import load_dotenv
from gno_plugin_knowledge_scrapper import get_artifacts_dir

# Load .env file at the start of the file
load_dotenv()

GNO_DOCS_URL = "https://github.com/gnolang/gno/tree/master/docs"

def extract_github_content() -> dict[str, str]:
    """
    Extract content from all .md files in Gno docs repository including subfolders
    
    Returns:
        Dictionary with file paths as keys and their content as values
    """
    results = {}
    
    # Parse GitHub URL
    parts = urlparse(GNO_DOCS_URL).path.split('/')
    owner = "gnolang"
    repo = "gno"
    branch = "master"
    base_path = "docs"
    
    # GitHub API URL for recursive tree listing
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    
    # Add GitHub token if available
    headers = {}
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    try:
        # Get full repository tree (including all subfolders)
        print("Fetching repository structure...")
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        tree = response.json()
        
        # Find all markdown files in docs folder and subfolders
        md_files = [
            item for item in tree['tree']
            if item['type'] == 'blob' 
            and item['path'].startswith(base_path) 
            and item['path'].endswith('.md')
        ]
        
        print(f"Found {len(md_files)} markdown files in repository")
        
        # Get content of each markdown file
        for item in md_files:
            try:
                # Get file content
                file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{item['path']}?ref={branch}"
                file_response = requests.get(file_url, headers=headers)
                file_response.raise_for_status()
                content = base64.b64decode(file_response.json()['content']).decode('utf-8')
                
                # Store relative path and content
                relative_path = item['path'][len(base_path):].lstrip('/')
                parent_folder = str(Path(relative_path).parent)
                results[relative_path] = (parent_folder if parent_folder != '.' else 'root', content)
                
                print(f"Retrieved: {item['path']}")
                time.sleep(1)  # Increased sleep time to be more conservative with rate limits
                
            except Exception as e:
                print(f"Error retrieving {item['path']}: {str(e)}", file=sys.stderr)
                continue
                
    except Exception as e:
        print(f"Error accessing GitHub: {str(e)}", file=sys.stderr)
    
    return results

def main():
    # Get script-specific artifacts directory
    artifacts_dir = get_artifacts_dir('docs_extractor')
    
    try:
        print(f"Starting extraction from {GNO_DOCS_URL}")
        md_contents = extract_github_content()
        
        if not md_contents:
            print("No markdown files found.")
            return
        
        # Generate output filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(artifacts_dir, f"gno_docs_{timestamp}.txt")
        
        # Write results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Found {len(md_contents)} markdown files from Gno documentation\n")
            f.write(f"Source: https://docs.gno.land\n")
            f.write("-" * 80 + "\n")
            
            # Sort files by folder for better organization
            sorted_files = sorted(md_contents.items(), key=lambda x: (x[1][0], x[0]))
            
            current_folder = None
            for file_path, (folder, content) in sorted_files:
                if folder != current_folder:
                    f.write(f"\n{'=' * 40} Folder: {folder} {'=' * 40}\n\n")
                    current_folder = folder
                
                f.write(f"File: {file_path}\n")
                f.write("-" * 80 + "\n")
                f.write(content + "\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"Content has been written to {output_file}")
        print(f"Total files extracted: {len(md_contents)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
