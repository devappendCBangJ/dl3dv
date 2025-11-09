#!/usr/bin/env python3
"""Reorganize downloaded DL3DV dataset to COLMAP standard structure

This script reorganizes the downloaded dataset from:
    output_dir/batch/hash_name/
    
To COLMAP structure:
    output_dir/hash_name/
    ├── sparse/0/
    │   ├── images.bin (or images.txt)
    │   ├── cameras.bin (or cameras.txt)
    │   └── points3D.bin (or points3D.txt)
    ├── images/
    │   ├── frame_00001.png
    │   └── ...
    └── transforms.json
"""

import os
import shutil
import argparse
from pathlib import Path
from tqdm import tqdm


def reorganize_to_colmap_structure(extracted_path: str, scene_name: str, output_dir: str):
    """ Reorganize extracted files to COLMAP standard structure
    
    :param extracted_path: Path to the extracted folder (batch/hash_name)
    :param scene_name: Scene name (hash_name) 
    :param output_dir: Root output directory
    """
    extracted_folder = Path(extracted_path)
    scene_folder = Path(output_dir) / scene_name
    
    # Create COLMAP structure
    scene_folder.mkdir(parents=True, exist_ok=True)
    images_folder = scene_folder / 'images'
    sparse_folder = scene_folder / 'sparse' / '0'
    images_folder.mkdir(parents=True, exist_ok=True)
    sparse_folder.mkdir(parents=True, exist_ok=True)
    
    # Collect all images from images_* folders
    image_dirs = sorted([d for d in extracted_folder.iterdir() if d.is_dir() and d.name.startswith('images_')])
    
    image_count = 0
    for img_dir in image_dirs:
        # Move all images from images_X to images/
        for img_file in sorted(img_dir.glob('*.png')):
            # Use original filename, but if duplicate exists, rename
            dest_file = images_folder / img_file.name
            if dest_file.exists():
                # Add suffix if file already exists (from different camera view)
                stem = img_file.stem
                suffix = img_file.suffix
                dest_file = images_folder / f"{stem}_{img_dir.name}{suffix}"
            
            shutil.move(str(img_file), str(dest_file))
            image_count += 1
    
    # Handle transforms.json and COLMAP files
    transforms_json = extracted_folder / 'transforms.json'
    if transforms_json.exists():
        # Move transforms.json to scene folder (for reference)
        shutil.move(str(transforms_json), str(scene_folder / 'transforms.json'))
    
    # Check if COLMAP files already exist in extracted folder
    colmap_files = ['images.bin', 'images.txt', 'cameras.bin', 'cameras.txt', 
                    'points3D.bin', 'points3D.txt', 'points3D.ply']
    
    found_colmap = False
    for colmap_file in colmap_files:
        source_file = extracted_folder / colmap_file
        if source_file.exists():
            shutil.move(str(source_file), str(sparse_folder / colmap_file))
            found_colmap = True
    
    # Check in subdirectories (including colmap/sparse/0/ structure)
    for subdir in extracted_folder.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('images_'):
            # First check direct files in subdir
            for colmap_file in colmap_files:
                source_file = subdir / colmap_file
                if source_file.exists():
                    shutil.move(str(source_file), str(sparse_folder / colmap_file))
                    found_colmap = True

            # Check for colmap/sparse/0/ structure (common in colmap_cache downloads)
            sparse_0_dir = subdir / 'sparse' / '0'
            if sparse_0_dir.exists():
                for colmap_file in colmap_files:
                    source_file = sparse_0_dir / colmap_file
                    if source_file.exists():
                        shutil.move(str(source_file), str(sparse_folder / colmap_file))
                        found_colmap = True
    
    return found_colmap, image_count


def reorganize_dataset(input_dir: str, output_dir: str, batch_name: str = None, scene_name: str = None):
    """ Reorganize entire dataset or specific scene
    
    :param input_dir: Input directory containing batch folders (e.g., images/1K/)
    :param output_dir: Output directory for COLMAP structure
    :param batch_name: Optional batch name (e.g., '1K'). If None, processes all batches
    :param scene_name: Optional specific scene name (hash). If None, processes all scenes
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Determine which folders to process
    if scene_name:
        # Process specific scene
        if batch_name:
            batch_folders = [input_path / batch_name]
        else:
            # Find scene in any batch folder
            batch_folders = [b for b in input_path.iterdir() if b.is_dir()]
        
        scenes_to_process = []
        for batch_folder in batch_folders:
            scene_folder = batch_folder / scene_name
            if scene_folder.exists():
                scenes_to_process.append((batch_folder.name, scene_name, scene_folder))
                break
    else:
        # Process all scenes
        if batch_name:
            batch_folders = [input_path / batch_name] if (input_path / batch_name).exists() else []
        else:
            batch_folders = [b for b in input_path.iterdir() if b.is_dir()]
        
        scenes_to_process = []
        for batch_folder in batch_folders:
            for scene_folder in batch_folder.iterdir():
                if scene_folder.is_dir():
                    scenes_to_process.append((batch_folder.name, scene_folder.name, scene_folder))
    
    if not scenes_to_process:
        print(f"No scenes found to process in {input_dir}")
        return
    
    print(f"Found {len(scenes_to_process)} scene(s) to reorganize")
    
    success_count = 0
    skip_count = 0
    
    for batch_name, scene_name, scene_folder in tqdm(scenes_to_process, desc='Reorganizing'):
        # Check if already reorganized (skip only if both images and sparse files exist)
        target_scene = output_path / scene_name
        images_exist = (target_scene / 'images').exists() and len(list((target_scene / 'images').glob('*.png'))) > 0
        sparse_exist = (target_scene / 'sparse' / '0').exists() and (
            (target_scene / 'sparse' / '0' / 'images.bin').exists() or
            (target_scene / 'sparse' / '0' / 'images.txt').exists()
        )
        if target_scene.exists() and images_exist and sparse_exist:
            skip_count += 1
            continue
        
        try:
            found_colmap, image_count = reorganize_to_colmap_structure(
                str(scene_folder), scene_name, str(output_path)
            )
            success_count += 1
            if image_count > 0:
                print(f"✓ {scene_name}: {image_count} images, COLMAP files: {found_colmap}")
        except Exception as e:
            print(f"✗ Error processing {scene_name}: {e}")
    
    print(f"\nSummary:")
    print(f"  Successfully reorganized: {success_count} scene(s)")
    print(f"  Skipped (already exists): {skip_count} scene(s)")
    print(f"  Output directory: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reorganize DL3DV dataset to COLMAP structure')
    parser.add_argument('--input_dir', type=str, required=True,
                        help='Input directory containing batch folders (e.g., images/1K/)')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Output directory for COLMAP structure')
    parser.add_argument('--batch', type=str, default=None,
                        help='Optional: specific batch name (e.g., 1K). If not specified, processes all batches')
    parser.add_argument('--scene', type=str, default=None,
                        help='Optional: specific scene name (hash). If not specified, processes all scenes')
    
    args = parser.parse_args()
    
    reorganize_dataset(args.input_dir, args.output_dir, args.batch, args.scene)

