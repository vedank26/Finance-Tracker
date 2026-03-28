import os
import shutil

def clean_pycache():
    """Clean all __pycache__ directories"""
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing: {pycache_path}")
            shutil.rmtree(pycache_path)
    
    print("Cache cleanup completed!")

if __name__ == '__main__':
    clean_pycache()
