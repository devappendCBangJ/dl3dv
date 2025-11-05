#!/usr/bin/env python3
# load library
import argparse
import subprocess
from pathlib import Path
from tqdm import tqdm

def run_colmap_undistort(scene_name: str, input_dir: Path, output_dir: Path):
    """
    Run COLMAP image_undistorter for a single scene.

    Args:
        scene_name: Name of the scene
        base_dir: Base directory containing all scenes
        output_base_dir: Output base directory
    """
    # scene path
    scene_path = input_dir/scene_name
    image_path = scene_path/"images"
    sparse_path = scene_path/"sparse"/"0"
    output_path = output_dir/scene_name

    if not image_path.exists() or not sparse_path.exists():
        print(f"⚠️  Skipping {scene_name}: images or sparse/0 directory not found")
        return False
    output_path.mkdir(parents=True, exist_ok=True)

    # set COLMAP
    cmd = [
        "colmap", "image_undistorter",
        "--image_path", str(image_path),
        "--input_path", str(sparse_path),
        "--output_path", str(output_path),
        "--output_type", "COLMAP"
    ]

    print(f"\n{'='*60}")
    print(f"Processing scene: {scene_name}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")

    # run COLMAP
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Successfully processed {scene_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error processing {scene_name}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    # setup arg
    parser = argparse.ArgumentParser(
        description="Undistort images for all scenes using COLMAP image_undistorter"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="data/dl3dv"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/dl3dv_undistorted"
    )
    args = parser.parse_args()

    # scene path
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: {input_dir} does not exist")
        return

    scenes = [d.name for d in input_dir.iterdir() if d.is_dir()]
    scenes.sort()

    print(f"Found {len(scenes)} scenes in {input_dir}")
    print(f"Scenes: {', '.join(scenes)}")
    print(f"\nOutput will be saved to: {output_dir}")

    # undistort
    success_count = 0
    failed_scenes = []

    for scene in tqdm(scenes, desc="Processing scenes"):
        success = run_colmap_undistort(scene, input_dir, output_dir)
        if success:
            success_count += 1
        else:
            failed_scenes.append(scene)

    # summary
    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"Total scenes: {len(scenes)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(failed_scenes)}")
    if failed_scenes:
        print(f"\nFailed scenes:")
        for scene in failed_scenes:
            print(f"- {scene}")

if __name__ == "__main__":
    main()
