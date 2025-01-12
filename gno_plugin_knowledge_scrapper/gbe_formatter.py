import os
import shutil
from gno_plugin_knowledge_scrapper import get_artifacts_dir

def clean_file_content(content: str) -> str:
    """
    Clean the file content by removing unwanted lines
    """
    lines_to_remove = [
        "Gno by Example is a community project.",
        "Check out the GitHub repo.",
        "Learn more about Gno.land and",
        "be part of the conversation:",
        "Check out the full example here.",
    ]
    
    # Split content into lines
    content_lines = content.splitlines()
    
    # Filter out unwanted lines and empty lines at the start
    cleaned_lines = []
    started_content = False
    for line in content_lines:
        if not started_content:
            if line.strip() and not any(remove in line for remove in lines_to_remove):
                started_content = True
                cleaned_lines.append(line)
        else:
            if not any(remove in line for remove in lines_to_remove):
                cleaned_lines.append(line)
    
    # Remove empty lines at the end
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def format_gbe_files():
    """
    Format all files in the gbe_crawler artifacts directory and save to gbe_formatter directory
    """
    crawler_dir = get_artifacts_dir('gbe_crawler')
    formatter_dir = get_artifacts_dir('gbe_formatter')
    
    print("\nProcessing GBE crawler files...")
    
    # Process each file in the directory
    for filename in os.listdir(crawler_dir):
        if not filename.endswith('.txt'):
            continue
            
        input_path = os.path.join(crawler_dir, filename)
        output_path = os.path.join(formatter_dir, filename)
        print(f"Formatting: {filename}")
        
        try:
            # Read content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean content
            cleaned_content = clean_file_content(content)
            
            # Write to new location
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

def main():
    try:
        print("Starting GBE formatter...")
        format_gbe_files()
        print("\nFormatting complete!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
