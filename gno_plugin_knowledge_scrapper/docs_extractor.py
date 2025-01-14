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
from openai import OpenAI

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
        
        # Generate timestamp for the folder
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_dir = os.path.join(artifacts_dir, f"gno_docs_{timestamp}")
        docs_dir = os.path.join(output_dir, "docs")  # Single folder for all docs
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(docs_dir, exist_ok=True)
        
        # Sort files by folder for better organization
        sorted_files = sorted(md_contents.items(), key=lambda x: (x[1][0], x[0]))
        
        # Create index file with keywords
        index_file = os.path.join(output_dir, "_index.txt")
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(f"Found {len(md_contents)} markdown files from Gno documentation\n")
            f.write(f"Source: https://docs.gno.land\n")
            f.write("-" * 80 + "\n\n")
            f.write("File Name | Keywords\n")
            f.write("-" * 80 + "\n")
            
            # Initialize OpenAI client
            client = OpenAI()
            
            for file_path, (folder, content) in sorted_files:
                print(f"Analyzing: {file_path}")
                try:
                    # Query ChatGPT for keywords
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a technical documentation analyzer. Extract exactly 10 relevant keywords or key phrases from the given text, separated by commas. Focus on technical terms, concepts, and important topics."},
                            {"role": "user", "content": content}
                        ],
                        temperature=0.3
                    )
                    
                    # Extract keywords from response
                    keywords = response.choices[0].message.content.strip()
                    
                    # Use the same safe filename format
                    safe_filename = file_path.replace('/', '_')
                    
                    # Write to index using the safe filename
                    f.write(f"{safe_filename} | {keywords}\n")
                    
                    # Write the file with its original path in the content
                    with open(os.path.join(docs_dir, safe_filename), 'w', encoding='utf-8') as doc_f:
                        doc_f.write(f"Original path: {folder}/{file_path}\n")
                        doc_f.write(f"Keywords: {keywords}\n")
                        doc_f.write("-" * 80 + "\n\n")
                        doc_f.write(content)
                    
                    # Add a small delay to respect rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
                    # Write to index without keywords if there's an error
                    f.write(f"{safe_filename} | Error extracting keywords\n")
        
        print(f"Content has been written to {output_dir}")
        print(f"Total files extracted: {len(md_contents)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
