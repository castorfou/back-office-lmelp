#!/usr/bin/env python3
"""
Generate favicon files in multiple sizes from a source PNG image.

This script creates all the necessary favicon formats for web applications:
- Standard sizes: 16x16, 32x32, 48x48
- Apple touch icon: 180x180
- Android/PWA: 192x192, 512x512
- ICO file with multiple sizes
"""

from pathlib import Path

from PIL import Image


def generate_favicons(source_path: str, output_dir: str) -> None:
    """
    Generate favicon files in multiple sizes.

    Args:
        source_path: Path to source PNG image (should be high resolution)
        output_dir: Directory where favicon files will be created
    """
    source = Path(source_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Open source image
    img = Image.open(source)
    print(f"Source image: {source} ({img.size[0]}x{img.size[1]})")

    # Define sizes to generate
    sizes = {
        "favicon-16x16.png": (16, 16),
        "favicon-32x32.png": (32, 32),
        "favicon-48x48.png": (48, 48),
        "apple-touch-icon.png": (180, 180),
        "android-chrome-192x192.png": (192, 192),
        "android-chrome-512x512.png": (512, 512),
    }

    # Generate PNG files
    for filename, size in sizes.items():
        resized = img.resize(size, Image.Resampling.LANCZOS)
        output_path = output / filename
        resized.save(output_path, "PNG")
        print(f"Created: {output_path} ({size[0]}x{size[1]})")

    # Generate ICO file with multiple sizes
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    ico_images = [img.resize(size, Image.Resampling.LANCZOS) for size in ico_sizes]
    ico_path = output / "favicon.ico"
    ico_images[0].save(
        ico_path, format="ICO", sizes=ico_sizes, append_images=ico_images[1:]
    )
    print(f"Created: {ico_path} (multi-size ICO)")

    print(f"\n✅ All favicons generated successfully in {output}")


if __name__ == "__main__":
    # Paths relative to this script location
    script_dir = Path(__file__).parent
    source_image = script_dir.parent / "gimp_favicon" / "favicon_back-office-lmelp.png"
    output_directory = script_dir.parent

    generate_favicons(str(source_image), str(output_directory))
