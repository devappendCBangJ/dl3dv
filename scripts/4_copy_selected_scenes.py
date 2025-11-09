#!/usr/bin/env python3
"""Copy selected scenes from dl3dv_colmap to dl3dv

This script selectively copies COLMAP-structured scenes based on:
- Specific hash(es)
- Hash list from file
- All scenes

Usage examples:
  # Copy single scene
  python scripts/copy_selected_scenes.py --input_dir data/dl3dv_colmap --output_dir data/dl3dv --hash abc123

  # Copy multiple scenes
  python scripts/copy_selected_scenes.py --input_dir data/dl3dv_colmap --output_dir data/dl3dv --hash_list "abc123,def456"

  # Copy from hash file
  python scripts/copy_selected_scenes.py --input_dir data/dl3dv_colmap --output_dir data/dl3dv --hash_file hashes.txt

  # Copy all scenes
  python scripts/copy_selected_scenes.py --input_dir data/dl3dv_colmap --output_dir data/dl3dv --all
"""

import os
import shutil
import argparse
from pathlib import Path
from tqdm import tqdm


def get_scene_list(input_dir: str, hash_name: str, hash_list: list, copy_all: bool):
    """Get list of scenes to copy

    :param input_dir: Input directory containing scene folders
    :param hash_name: Single hash to copy
    :param hash_list: List of hashes to copy
    :param copy_all: If True, copy all scenes
    :return: List of scene names (hash names)
    """
    input_path = Path(input_dir)

    # If copy_all is set, get all scene folders
    if copy_all:
        all_scenes = [f.name for f in input_path.iterdir() if f.is_dir() and not f.name.startswith('.')]
        return sorted(all_scenes)

    # If hash_list is provided, use it
    if hash_list and len(hash_list) > 0:
        scenes = []
        for h in hash_list:
            h = h.strip()
            if h == '':
                continue
            scene_path = input_path / h
            if not scene_path.exists():
                print(f"Warning: Scene '{h}' not found in {input_dir}")
                continue
            scenes.append(h)
        return scenes

    # If single hash is provided
    if hash_name != '':
        scene_path = input_path / hash_name
        if not scene_path.exists():
            print(f"Error: Scene '{hash_name}' not found in {input_dir}")
            return []
        return [hash_name]

    return []


def copy_scene(scene_name: str, input_dir: str, output_dir: str, overwrite: bool = False):
    """Copy a single scene from input to output directory

    :param scene_name: Scene name (hash)
    :param input_dir: Source directory
    :param output_dir: Destination directory
    :param overwrite: If True, overwrite existing files
    :return: Tuple of (success: bool, status: str) where status is 'copied', 'partial', or 'skipped'
    """
    input_path = Path(input_dir) / scene_name
    output_path = Path(output_dir) / scene_name

    # Check if source exists
    if not input_path.exists():
        return False, 'error'

    # Check if destination exists
    if output_path.exists():
        if not overwrite:
            # Smart partial copy: copy only missing subdirectories
            images_src = input_path / 'images'
            sparse_src = input_path / 'sparse'
            images_dst = output_path / 'images'
            sparse_dst = output_path / 'sparse'

            copied_something = False

            # Helper function to check if directory is empty or missing
            def is_empty_or_missing(path):
                if not path.exists():
                    return True
                # Check if directory has any files (recursively)
                try:
                    for root, dirs, files in os.walk(path):
                        if files:  # If any files found, not empty
                            return False
                    return True  # No files found, directory is empty
                except:
                    return False

            # Copy images if missing or empty
            if images_src.exists() and is_empty_or_missing(images_dst):
                try:
                    if images_dst.exists():
                        shutil.rmtree(images_dst)  # Remove empty directory
                    shutil.copytree(images_src, images_dst)
                    copied_something = True
                except Exception as e:
                    print(f"Error copying images for {scene_name}: {e}")
                    return False, 'error'

            # Copy sparse if missing or empty
            if sparse_src.exists() and is_empty_or_missing(sparse_dst):
                try:
                    if sparse_dst.exists():
                        shutil.rmtree(sparse_dst)  # Remove empty directory
                    shutil.copytree(sparse_src, sparse_dst)
                    copied_something = True
                except Exception as e:
                    print(f"Error copying sparse for {scene_name}: {e}")
                    return False, 'error'

            if copied_something:
                return True, 'partial'
            else:
                return False, 'skipped'  # Both images and sparse already exist
        else:
            # Remove existing directory
            shutil.rmtree(output_path)

    # Copy the entire scene directory
    try:
        shutil.copytree(input_path, output_path)
        return True, 'copied'
    except Exception as e:
        print(f"Error copying {scene_name}: {e}")
        return False, 'error'


def copy_scenes(input_dir: str, output_dir: str, hash_name: str, hash_list: list,
                copy_all: bool, overwrite: bool):
    """Copy selected scenes from input to output directory

    :param input_dir: Source directory containing scene folders
    :param output_dir: Destination directory
    :param hash_name: Single hash to copy
    :param hash_list: List of hashes to copy
    :param copy_all: If True, copy all scenes
    :param overwrite: If True, overwrite existing scenes
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Validate input directory
    if not input_path.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Get list of scenes to copy
    scenes_to_copy = get_scene_list(input_dir, hash_name, hash_list, copy_all)

    if not scenes_to_copy:
        print("No scenes to copy.")
        return

    print(f"Found {len(scenes_to_copy)} scene(s) to copy")
    print(f"Source: {input_dir}")
    print(f"Destination: {output_dir}\n")

    # Copy scenes
    success_count = 0
    partial_count = 0
    skip_count = 0
    error_count = 0

    for scene_name in tqdm(scenes_to_copy, desc='Copying scenes'):
        success, status = copy_scene(scene_name, input_dir, output_dir, overwrite)

        if success:
            if status == 'copied':
                success_count += 1
            elif status == 'partial':
                partial_count += 1
        elif status == 'skipped':
            skip_count += 1
        else:
            error_count += 1

    # Print summary
    print(f"\nSummary:")
    print(f"  Successfully copied (full): {success_count} scene(s)")
    print(f"  Partially copied (images or sparse): {partial_count} scene(s)")
    print(f"  Skipped (already exists): {skip_count} scene(s)")
    print(f"  Failed: {error_count} scene(s)")
    print(f"  Destination: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Copy selected scenes from source to destination directory'
    )

    # Required arguments
    parser.add_argument('--input_dir', type=str, required=True,
                        help='Input directory containing scene folders (e.g., data/dl3dv_colmap)')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Output directory for copied scenes (e.g., data/dl3dv)')

    # Selection options (mutually exclusive group would be ideal, but allowing combinations)
    parser.add_argument('--hash', type=str, default='',
                        help='Single scene hash to copy')
    parser.add_argument('--hash_list', type=str, default='',
                        help='Comma-separated list of hash codes to copy (e.g., "hash1,hash2,hash3")')
    parser.add_argument('--hash_file', type=str, default='',
                        help='Path to a text file containing hash codes to copy (one hash per line)')
    parser.add_argument('--all', action='store_true',
                        help='Copy all scenes from input directory')

    # Additional options
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite existing scenes in output directory')

    args = parser.parse_args()

    # Process hash_file if provided
    hash_list_from_file = []
    if args.hash_file:
        if not os.path.exists(args.hash_file):
            print(f'ERROR: Hash file {args.hash_file} not found.')
            exit(1)
        with open(args.hash_file, 'r') as f:
            hash_list_from_file = [line.strip() for line in f if line.strip()]

    # Combine hash_list from command line and file
    hash_list = []
    if args.hash_list:
        hash_list = [h.strip() for h in args.hash_list.split(',') if h.strip()]
    if hash_list_from_file:
        hash_list.extend(hash_list_from_file)

    # Remove duplicates while preserving order
    seen = set()
    hash_list = [h for h in hash_list if not (h in seen or seen.add(h))]

    # Validate arguments
    if not args.all and not args.hash and not hash_list:
        print('ERROR: Must specify either --all, --hash, --hash_list, or --hash_file')
        exit(1)

    # Copy scenes
    copy_scenes(args.input_dir, args.output_dir, args.hash, hash_list, args.all, args.overwrite)
