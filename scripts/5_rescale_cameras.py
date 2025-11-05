#!/usr/bin/env python3
"""
Rescale camera parameters in COLMAP sparse models to match actual image resolutions.
Uses COLMAP's model_converter to convert to text, modify, and convert back to binary.
"""
import argparse
import shutil
import subprocess
import re
from pathlib import Path
from PIL import Image
from tqdm import tqdm


def get_image_resolution(image_dir: Path):
    """
    Get the resolution of the first image in the directory.

    Returns:
        Tuple of (width, height) or None if no images found
    """
    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']

    for ext in image_extensions:
        images = list(image_dir.glob(f'*{ext}'))
        if images:
            img = Image.open(images[0])
            return img.size
    return None


def rescale_cameras_for_scene(scene_name: str, input_dir: Path, backup: bool = True):
    """
    Rescale camera parameters for a single scene if resolution mismatch is detected.

    Args:
        scene_name: Name of the scene
        input_dir: Base directory containing all scenes
        backup: Whether to create a backup of the original sparse model

    Returns:
        Tuple of (success, message)
    """
    # check dir
    scene_path = input_dir / scene_name
    image_dir = scene_path / "images"
    sparse_dir = scene_path / "sparse" / "0"

    if not image_dir.exists():
        return False, f"Images directory not found"
    if not sparse_dir.exists():
        return False, f"Sparse/0 directory not found"

    # image resolution
    image_res = get_image_resolution(image_dir)
    if image_res is None:
        return False, f"No images found in {image_dir}"

    img_w, img_h = image_res

    # temp txt dir
    txt_dir = sparse_dir.parent / "0_txt_temp"
    txt_dir.mkdir(exist_ok=True)

    try:
        # convert bin2txt
        cmd = [
            "colmap", "model_converter",
            "--input_path", str(sparse_dir),
            "--output_path", str(txt_dir),
            "--output_type", "TXT"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # read sparse
        cam_file = txt_dir / "cameras.txt"
        if not cam_file.exists():
            return False, "cam.txt not found after conversion"

        with open(cam_file, 'r') as f:
            lines = f.readlines()

        # rescale sparse
        modified = False
        new_lines = []
        for line in lines:
            if line.startswith('#') or line.strip() == '':
                new_lines.append(line)
                continue

            parts = line.strip().split()
            if len(parts) < 5:
                new_lines.append(line)
                continue

            # parse sparse line (CAMERA_ID MODEL WIDTH HEIGHT PARAMS[])
            cam_id = parts[0]
            model = parts[1]
            old_w = int(parts[2])
            old_h = int(parts[3])
            params = [float(p) for p in parts[4:]]

            # rescale sparse
            if old_w == img_w and old_h == img_h:
                new_lines.append(line)
                continue

            scale_x = img_w / old_w
            scale_y = img_h / old_h
            if len(params) >= 4:
                params[0] *= scale_x  # fx
                params[1] *= scale_y  # fy
                params[2] *= scale_x  # cx
                params[3] *= scale_y  # cy

            # new sparse line
            params_str = ' '.join([f"{p:.10f}" for p in params])
            new_line = f"{cam_id} {model} {img_w} {img_h} {params_str}\n"
            new_lines.append(new_line)
            modified = True
            
        # etc
        if not modified:
            shutil.rmtree(txt_dir)
            return True, f"Camera already matches ({img_w}x{img_h})"

        if backup:
            backup_dir = scene_path / "sparse" / "0_backup"
            if not backup_dir.exists():
                shutil.copytree(sparse_dir, backup_dir)

        # write new sparse
        with open(cam_file, 'w') as f:
            f.writelines(new_lines)

        # convert txt2bin
        cmd = [
            "colmap", "model_converter",
            "--input_path", str(txt_dir),
            "--output_path", str(sparse_dir),
            "--output_type", "BIN"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # clean up temp dir
        shutil.rmtree(txt_dir)
        return True, f"Rescaled from {old_w}x{old_h} to {img_w}x{img_h}"

    # clean up on error
    except subprocess.CalledProcessError as e:
        if txt_dir.exists():
            shutil.rmtree(txt_dir)
        return False, f"COLMAP error: {e.stderr}"
    except Exception as e:
        if txt_dir.exists():
            shutil.rmtree(txt_dir)
        return False, f"Error: {str(e)}"

def main():
    # setup args
    parser = argparse.ArgumentParser(
        description="Rescale COLMAP camera parameters to match actual image resolutions"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="data/dl3dv",
        help="Input directory containing all scenes"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup of original sparse models"
    )
    parser.add_argument(
        "--scene",
        type=str,
        help="Process only a specific scene (optional)"
    )
    args = parser.parse_args()

    # scene list
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: {input_dir} does not exist")
        exit(1)

    if args.scene:
        scenes = [args.scene]
        if not (input_dir / args.scene).exists():
            print(f"Error: Scene '{args.scene}' not found in {input_dir}")
            return
    else:
        scenes = [d.name for d in input_dir.iterdir() if d.is_dir()]
        scenes.sort()

    print(f"Processing {len(scenes)} scene(s) in {input_dir}")
    if not args.no_backup:
        print("Backups will be created in sparse/0_backup")
    print()

    # rescale sparse
    results = {
        'success': [],
        'already_correct': [],
        'failed': []
    }
    
    for scene in tqdm(scenes, desc="Processing scenes"):
        success, message = rescale_cameras_for_scene(
            scene,
            input_dir,
            backup=not args.no_backup
        )

        if success:
            if "already match" in message:
                results['already_correct'].append((scene, message))
                tqdm.write(f"✓ {scene}: {message}")
            else:
                results['success'].append((scene, message))
                tqdm.write(f"✓ {scene}: {message}")
        else:
            results['failed'].append((scene, message))
            tqdm.write(f"✗ {scene}: {message}")

    # print summary
    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"Total scenes: {len(scenes)}")
    print(f"Successfully rescaled: {len(results['success'])}")
    print(f"Already correct: {len(results['already_correct'])}")
    print(f"Failed: {len(results['failed'])}")

    if results['failed']:
        print(f"\nFailed scenes:")
        for scene, message in results['failed']:
            print(f"  - {scene}: {message}")

if __name__ == "__main__":
    main()
