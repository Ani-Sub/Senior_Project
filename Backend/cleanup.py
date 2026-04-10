"""
Cleanup script - run after importing data to database.
Deletes output/latest/ folder and all contents.
"""

from utility.output import cleanup_output

if __name__ == "__main__":
    cleanup_output()
