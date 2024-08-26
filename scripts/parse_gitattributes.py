#!/usr/bin/env python3

import os
import shutil


def process_gitattributes():
    if not os.path.exists('.gitattributes'):
        # This was before we added the file to the repo
        return

    with open('.gitattributes', 'r') as f:
        for line in f:
            line = line.strip()
            if 'export-ignore' in line:
                file_to_remove = line.split()[0]
                print(f"DEBUG: Attempting to remove: {file_to_remove}")
                if os.path.exists(file_to_remove):
                    if os.path.isdir(file_to_remove):
                        shutil.rmtree(file_to_remove)
                    else:
                        os.remove(file_to_remove)
                        print(f"DEBUG: Removed {file_to_remove}")
                else:
                    print(f"DEBUG: File not found: {file_to_remove}")


if __name__ == "__main__":
    process_gitattributes()
