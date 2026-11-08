import os
import shutil
from pathlib import Path

def clean_pycache():
    """Clean all __pycache__ directories across the project, skipping virtual environments"""
    project_root = Path(__file__).resolve().parent.parent.parent
    skip_dirs = {'venv', '.venv', 'env', '.git', '.terraform'}
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing: {pycache_path}")
            shutil.rmtree(pycache_path, ignore_errors=True)
            dirs.remove('__pycache__')

    print("Cache cleanup completed!")

if __name__ == '__main__':
    clean_pycache()
