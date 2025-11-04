#!/usr/bin/env python3
"""Copy the first image from each folder in images/1K to sample folder"""

import os
import shutil
import argparse
from pathlib import Path
from glob import glob

def copy_first_image(input_dir, output_dir):
    """Copy the first image from each hash folder to destination"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create destination directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all hash folders in source directory
    hash_folders = [f for f in input_path.iterdir() if f.is_dir()]
    
    copied_count = 0
    skipped_count = 0
    
    for hash_folder in sorted(hash_folders):
        hash_name = hash_folder.name
        
        # Find all PNG images in this folder (including subdirectories like images_8)
        image_files = sorted(hash_folder.rglob("*.png"))
        
        if not image_files:
            print(f"No images found in {hash_name}")
            skipped_count += 1
            continue
        
        # Get the first image
        first_image = image_files[0]
        
        # Destination file path with hash name as filename
        output_file = output_path / f"{hash_name}.png"
        
        # Copy the image
        try:
            shutil.copy2(first_image, output_file)
            print(f"Copied: {hash_name}.png (from {first_image.relative_to(input_path)})")
            copied_count += 1
        except Exception as e:
            print(f"Error copying {hash_name}: {e}")
            skipped_count += 1
    
    print(f"\nSummary:")
    print(f"  Copied: {copied_count} images")
    print(f"  Skipped: {skipped_count} folders")
    print(f"  Destination: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Copy the first image from each folder in source directory to destination"
    )
    parser.add_argument(
        "--input_dir",
        "-i",
        type=str,
        required=True,
        help="Input directory containing hash folders"
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        required=True,
        help="Output directory for copied images"
    )
    
    args = parser.parse_args()
    
    # Validate input directory exists
    if not Path(args.input_dir).exists():
        parser.error(f"Input directory does not exist: {args.input_dir}")
    
    if not Path(args.input_dir).is_dir():
        parser.error(f"Input path is not a directory: {args.input_dir}")
    
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}\n")
    
    copy_first_image(args.input_dir, args.output_dir)