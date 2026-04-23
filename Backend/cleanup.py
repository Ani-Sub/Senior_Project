"""
Cleanup script - run after importing data to database.
Deletes output/ folder and all contents.
"""

from pathlib import Path
from utility.output import cleanup_output

if __name__ == "__main__":
    # Get the Backend directory (where this script lives)
    backend_dir = Path(__file__).parent
    output_dir = backend_dir / "output"
    
    cleanup_output(output_dir)
