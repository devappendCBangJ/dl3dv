"""
Convert DL3DV label format to LERF-OVS label format
"""
import os
import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def convert_json_format(dl3dv_json, image_name, image_size):
    """Convert DL3DV JSON format to LERF-OVS format"""
    width, height = image_size

    lerf_json = {
        "info": {
            "name": image_name,
            "width": width,
            "height": height,
            "depth": 3,
            "note": ""
        },
        "objects": []
    }

    # Convert each shape to object
    for shape in dl3dv_json.get("shapes", []):
        obj = {
            "category": shape["label"],
            "group": shape.get("group_id", 0) if shape.get("group_id") is not None else 0,
            "segmentation": [shape["points"]]
        }
        lerf_json["objects"].append(obj)

    return lerf_json


def create_mask_from_polygon(polygon, image_size):
    """Create a binary mask from polygon points"""
    # Create a new image for the mask
    mask = Image.new('L', image_size, 0)
    draw = ImageDraw.Draw(mask)

    # Convert polygon points to flat list of tuples
    points = [tuple(pt) for pt in polygon]

    # Draw filled polygon
    draw.polygon(points, fill=255)

    return mask


def convert_labels(input_dir, output_dir, convert_to_jpg=False):
    """Convert all labels from dl3dv format to lerf_ovs format"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Create output directories
    output_path.mkdir(parents=True, exist_ok=True)
    gt_path = output_path / "gt"
    gt_path.mkdir(exist_ok=True)

    # Get all JSON files (excluding annotations.json)
    json_files = [f for f in input_path.glob("frame_*.json")]

    print(f"Found {len(json_files)} frames to convert")

    for json_file in sorted(json_files):
        frame_name = json_file.stem  # e.g., frame_00001
        print(f"Processing {frame_name}...")

        # Read dl3dv JSON
        with open(json_file, 'r') as f:
            dl3dv_json = json.load(f)

        # Find corresponding image (PNG or JPG)
        png_path = input_path / f"{frame_name}.png"
        jpg_path_input = input_path / f"{frame_name}.jpg"

        if png_path.exists():
            image_path = png_path
            image_ext = ".png"
        elif jpg_path_input.exists():
            image_path = jpg_path_input
            image_ext = ".jpg"
        else:
            print(f"  Warning: Image not found: {frame_name}")
            continue

        # Read image
        image = Image.open(image_path)
        if image is None:
            print(f"  Warning: Failed to read image: {image_path}")
            continue

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Save image to output directory
        if convert_to_jpg and image_ext == ".png":
            output_image_name = f"{frame_name}.jpg"
            output_image_path = output_path / output_image_name
            image.save(output_image_path, 'JPEG', quality=95)
            print(f"  Converted PNG to JPG: {output_image_name}")
        else:
            output_image_name = f"{frame_name}{image_ext}"
            output_image_path = output_path / output_image_name
            if image_ext == ".png":
                image.save(output_image_path, 'PNG')
            else:
                image.save(output_image_path, 'JPEG', quality=95)
            print(f"  Saved image: {output_image_name}")

        # Convert JSON format
        lerf_json = convert_json_format(dl3dv_json, output_image_name, image.size)

        # Save converted JSON
        json_output_path = output_path / f"{frame_name}.json"
        with open(json_output_path, 'w') as f:
            json.dump(lerf_json, f, indent=4)
        print(f"  Saved JSON: {frame_name}.json")

        # Create GT directory for this frame
        frame_gt_path = gt_path / frame_name
        frame_gt_path.mkdir(exist_ok=True)

        # Create mask for each object
        for obj in lerf_json["objects"]:
            category = obj["category"]

            # Create mask from polygon
            polygon = obj["segmentation"][0]
            mask = create_mask_from_polygon(polygon, image.size)

            # Save mask as grayscale image (0=background, 255=object)
            mask_filename = f"{category}.jpg"
            mask_path = frame_gt_path / mask_filename
            mask.save(mask_path, 'JPEG', quality=95)

        print(f"  Created {len(lerf_json['objects'])} GT masks")

    print(f"\nConversion complete!")
    print(f"Output directory: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert DL3DV label format to LERF-OVS format')
    parser.add_argument('--input_dir', type=str, help='Input directory containing DL3DV labels')
    parser.add_argument('--output_dir', type=str, help='Output directory for LERF-OVS labels')
    parser.add_argument('--convert-to-jpg', action='store_true',
                        help='Convert PNG images to JPG format')

    args = parser.parse_args()

    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Convert to JPG: {args.convert_to_jpg}")
    print()

    convert_labels(args.input_dir, args.output_dir, args.convert_to_jpg)
