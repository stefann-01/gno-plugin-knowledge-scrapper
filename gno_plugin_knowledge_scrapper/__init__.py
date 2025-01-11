import os
from pathlib import Path

def get_artifacts_dir(script_name: str) -> str:
    """
    Get artifacts directory for a specific script
    
    Args:
        script_name: Name of the script (e.g., 'docs_extractor', 'gbe_crawler')
        
    Returns:
        str: Path to script-specific artifacts directory
    """
    base_artifacts_dir = os.path.join(os.path.dirname(__file__), 'artifacts')
    script_artifacts_dir = os.path.join(base_artifacts_dir, script_name)
    os.makedirs(script_artifacts_dir, exist_ok=True)
    return script_artifacts_dir
