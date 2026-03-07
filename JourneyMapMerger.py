"""
JourneyMap Merger
=================

A utility for merging JourneyMap map tiles, waypoint NBT data, and
add-on JSON data from multiple JourneyMap folders or ZIP archives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path, PurePath
from typing import Dict, List, Tuple, Optional, Callable

import nbtlib
from PIL import Image
from nbtlib import Compound


# Terminal Colors
class TColor:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_MAGENTA = "\033[95m"


# Hashing
def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def image_visual_hash(path: Path) -> str:
    with Image.open(path) as im:
        rgba = im.convert("RGBA")
        return hashlib.sha256(rgba.tobytes()).hexdigest()


# Universal File Discovery
def discover_files(input_roots: List[Path], pattern: Optional[str] = "*", manual: bool = False,
                   fixed_paths: Optional[List[str]] = None, hash_func: Optional[Callable[[Path], str]] = None) -> Dict[
    PurePath, List[Tuple[Path, str]]]:
    if hash_func is None:
        hash_func = file_hash

    grouped: Dict[PurePath, List[Tuple[Path, str]]] = {}

    for root in input_roots:
        if fixed_paths:
            for rel_str in fixed_paths:
                rel = PurePath(rel_str)
                abs_path = root / rel
                if abs_path.is_file():
                    grouped.setdefault(rel, []).append((abs_path, hash_func(abs_path)))
        else:
            if pattern is None:
                continue
            for file in root.rglob(pattern):
                if file.is_file():
                    rel = PurePath(file).relative_to(root)
                    grouped.setdefault(rel, []).append((file, hash_func(file)))

    if not manual:
        for rel, items in grouped.items():
            grouped[rel] = sorted(items, key=lambda x: x[0].stat().st_mtime)

    return grouped


# ZIP Extraction
def extract_zip_if_needed(path: Path) -> Path:
    if path.is_file() and path.suffix.lower() == ".zip":
        extract_dir = path.parent / f"{path.stem}_unzipped"
        if not extract_dir.exists():
            print(f"Extracting ZIP: {path.name}")
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(extract_dir)
        return extract_dir
    return path


def zip_output_folder(folder: Path) -> None:
    print(f"{TColor.BRIGHT_MAGENTA}ZIPPING OUTPUT{TColor.RESET}")
    os.makedirs(folder.parent, exist_ok=True)
    shutil.make_archive(str(folder), "zip", root_dir=str(folder))
    try:
        shutil.rmtree(folder)
    except Exception as exc:
        print(f"{TColor.RED}Failed to remove temporary folder: {exc}{TColor.RESET}")
    print(f"{TColor.GREEN}  Zipping complete!{TColor.RESET}")


# Merge Functions
def merge_png_group(output_path: Path, entries: List[Tuple[Path, str]]) -> None:
    hashes = {h for _, h in entries}
    os.makedirs(output_path.parent, exist_ok=True)

    if len(hashes) == 1:
        shutil.copy2(entries[-1][0], output_path)
        return

    base = Image.open(entries[0][0]).convert("RGBA")
    for img_path, _ in entries[1:]:
        overlay = Image.open(img_path).convert("RGBA")
        base.alpha_composite(overlay)
    base.save(output_path, format="PNG", optimize=False, compress_level=9)


def merge_basic_file_group(output_path: Path, entries: List[Tuple[Path, str]]) -> None:
    os.makedirs(output_path.parent, exist_ok=True)
    # Get the latest file in the group
    shutil.copy2(entries[-1][0], output_path)


def merge_nbt_group(output_root: Path, entries: List[Tuple[Path, str]]) -> None:
    hashes = {h for _, h in entries}
    output_path = output_root

    if len(hashes) == 1:
        os.makedirs(output_path.parent, exist_ok=True)
        shutil.copy2(entries[-1][0], output_path)
        return

    roots = []
    for file, _ in entries:
        try:
            root = nbtlib.load(str(file))
            if isinstance(root, Compound):
                roots.append(root)
        except Exception:
            continue

    if not roots:
        return

    base = roots.pop(0)
    for root in roots:
        for key, val in root.items():
            base[key] = val

    final_file = nbtlib.File(base)
    os.makedirs(output_path.parent, exist_ok=True)
    final_file.save(str(output_path))


def merge_json_group(output_path: Path, entries: List[Tuple[Path, str]]) -> None:
    hashes = {h for _, h in entries}
    os.makedirs(output_path.parent, exist_ok=True)

    if len(hashes) == 1:
        shutil.copy2(entries[-1][0], output_path)
        return

    merged: Dict[str, dict] = {}

    for file, _ in entries:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "id" in item:
                            merged[item["id"]] = item
        except Exception:
            continue

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(list(merged.values()), f, indent=4)


def handle_maps(output_root: Path, input_roots: List[Path], manual: bool) -> None:
    print(f"{TColor.YELLOW}MAP MERGING{TColor.RESET}")
    print("  Reading map files...")
    groups = discover_files(input_roots, "*.png", manual, hash_func=image_visual_hash)

    if not groups:
        print("  No map files found. Skipping.")
        return

    total_files = sum(len(files) for files in groups.values())
    print(f"  Found {total_files} map files across {len(groups)} unique paths.")

    print("  Merging & saving map data...")
    for rel, entries in groups.items():
        merge_png_group(output_root / rel, entries)

    print(f"{TColor.GREEN}  Map merge complete!{TColor.RESET}")


def handle_regions(output_root: Path, input_roots: List[Path], manual: bool) -> None:
    print(f"{TColor.BLUE}REGION MERGING{TColor.RESET}")
    print(f"  NOTE: Region merging uses file-level overwrite only.")
    print("    The newest file wins (or input order with --manual).")
    print("    Partial or overlapping region data cannot be merged.")

    print("  Reading region files...")
    groups = discover_files(input_roots, "*.mca", manual)

    if not groups:
        print("  No region files found. Skipping.")
        return

    total_files = sum(len(files) for files in groups.values())
    print(f"  Found {total_files} region files across {len(groups)} unique paths.")

    print("  Merging & saving region data...")
    for rel, entries in groups.items():
        merge_basic_file_group(output_root / rel, entries)

    print(f"{TColor.GREEN}  Region merge complete!{TColor.RESET}")


def handle_nbt(output_root: Path, input_roots: List[Path], manual: bool) -> None:
    print(f"{TColor.CYAN}NBT MERGING{TColor.RESET}")

    print("  Reading NBT files...")
    groups = discover_files(input_roots, "*.dat", manual)
    groups.update(discover_files(input_roots, "*.nbt", manual))

    if not groups:
        print("  No NBT files found. Skipping.")
        return

    total_files = sum(len(files) for files in groups.values())
    print(f"  Found {total_files} NBT files across {len(groups)} unique paths.")

    print("  Merging & saving NBT data...")
    for rel, entries in groups.items():
        merge_nbt_group(output_root / rel, entries)

    print(f"{TColor.GREEN}  NBT merge complete!{TColor.RESET}")


def handle_json(output_root: Path, input_roots: List[Path], manual: bool) -> None:
    print(f"{TColor.MAGENTA}JSON MERGING{TColor.RESET}")
    print("  Reading JSON files...")
    groups = discover_files(input_roots, "*.json", manual)

    if not groups:
        print("  No JSON files found. Skipping.")
        return

    total_files = sum(len(files) for files in groups.values())
    print(f"  Found {total_files} JSON files across {len(groups)} unique paths.")

    print("  Merging & saving JSON data...")
    for rel, entries in groups.items():
        merge_json_group(output_root / rel, entries)

    print(f"{TColor.GREEN}  JSON merge complete!{TColor.RESET}")


def handle_other(output_root: Path, input_roots: List[Path], manual: bool) -> None:
    print(f"{TColor.YELLOW}OTHER FILE MERGING{TColor.RESET}")
    print(f'  NOTE: "Other" merging uses file-level overwrite only.')
    print("    The newest file wins (or input order with --manual).")
    print("    Partial or overlapping file data cannot be merged.")
    print("  Reading other files...")
    all_files = discover_files(input_roots, "*", manual)

    excluded = {".png", ".mca", ".json", ".dat", ".nbt"}
    filtered = {
        rel: entries
        for rel, entries in all_files.items()
        if rel.suffix.lower() not in excluded
    }

    if not filtered:
        print("  No other files found. Skipping.")
        return

    total_files = sum(len(files) for files in filtered.values())
    print(f"  Found {total_files} other files across {len(filtered)} unique paths")

    print("  Merging & saving data...")
    for rel, entries in filtered.items():
        merge_basic_file_group(output_root / rel, entries)

    print(f"{TColor.GREEN}  Other-file merge complete!{TColor.RESET}")


MERGE_HANDLERS = {
    "maps": handle_maps,
    "regions": handle_regions,
    "nbt": handle_nbt,
    "json": handle_json,
    "other": handle_other,
}


def prompt_yes_no() -> bool:
    while True:
        answer = input('Type "yes" (y) to continue, "no" (n) to cancel: ').lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Try again.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge JourneyMap map tiles, NBT (Waypoints), JSON (Addons), and other data."
    )

    parser.add_argument("out", type=str, help="Output folder for merged data.")
    parser.add_argument("layers", nargs="+", help="JourneyMap folders or ZIP files.")
    parser.add_argument("--manual", action="store_true", help="Preserve input order.")

    parser.add_argument("-m", "--maps", action="store_true", help="Only merge map tiles.")
    parser.add_argument("-r", "--regions", action="store_true", help="Only merge region .mca files.")
    parser.add_argument("-n", "--nbt", action="store_true", help="Only merge NBT (.dat/.nbt) files (Waypoints).")
    parser.add_argument("-j", "--json", action="store_true", help="Only merge JSON files (Mod Addons).")
    parser.add_argument("-o", "--other", action="store_true", help="Merge all other file types.")
    parser.add_argument("-a", "--all", action="store_true", help="Merge all file types.")


    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts.")
    parser.add_argument("-z", "--zip", action="store_true", help="Zip the merged output.")

    return parser.parse_args()


def main():
    args = parse_args()

    # If no specific merge modes were selected, enable all of them
    if not (args.maps or args.regions or args.nbt or args.json or args.other):
        args.maps = args.regions = args.nbt = args.json = True

    # If the all flag is selected. Use it
    if args.all:
        args.maps = args.regions = args.nbt = args.json = args.other = True

    output_path = Path(args.out)

    # If output ends with .zip, force zip mode
    if args.out.lower().endswith(".zip"):
        output_path = output_path.with_suffix("")
        args.zip = True

    input_paths = [extract_zip_if_needed(Path(p)) for p in args.layers]

    print("Validating input...")

    for p in input_paths:
        if not p.is_dir():
            print(f"{TColor.RED}Invalid directory: {p}{TColor.RESET}")
            sys.exit(1)

        if output_path.resolve().is_relative_to(p.resolve()):
            print(f"{TColor.RED}ERROR:{TColor.RESET} Output folder cannot be the same as/inside an input folder.")
            print(f"  Output: {output_path}")
            print(f"  Input:  {p}")
            sys.exit(1)

    if output_path.is_file():  # Should be impossible
        print(f"{TColor.RED}Output path is a file. Choose a folder.{TColor.RESET}")
        sys.exit(1)

    # Collapse Duplicate Paths
    input_paths = list(dict.fromkeys(input_paths))

    if not args.yes:
        print(f"Output: {output_path}{' (Zipped)' if args.zip else ''}")
        print("Inputs:")
        for p in input_paths:
            print(f" - {p}")

        print("\nMerging:")
        for mode in MERGE_HANDLERS:
            if getattr(args, mode):
                print(f" - {mode}")

        print("\nProceed?")
        if not prompt_yes_no():
            sys.exit(0)

        # Warn if ZIP output already exists
        if args.zip:
            zip_file = output_path.with_suffix(".zip")
            if zip_file.exists():
                print(f"{TColor.RED}Output ZIP exists: {zip_file}{TColor.RESET}")
                print("Overwrite?")
                if not prompt_yes_no():
                    print(f"{TColor.RED}Quitting...{TColor.RESET}")
                    sys.exit(0)

        # Check Output folder
        if output_path.is_dir() and any(output_path.iterdir()):
            if not args.yes:
                print(f"{TColor.RED}Output folder exists: {output_path}{TColor.RESET}")
                print("Overwrite?")
                if not prompt_yes_no():
                    print(f"{TColor.RED}Quitting...{TColor.RESET}")
                    sys.exit(0)

            # Remove Folder
            try:
                shutil.rmtree(output_path)
            except Exception as exc:
                print(f"{TColor.RED}Failed to clear output folder: {exc}{TColor.RESET}")
                sys.exit(1)

    os.makedirs(output_path, exist_ok=True)

    for mode, handler in MERGE_HANDLERS.items():
        if getattr(args, mode):
            handler(output_path, input_paths, args.manual)

    if args.zip:
        zip_output_folder(output_path)

    print(f"\n{TColor.BRIGHT_GREEN}All merges completed!{TColor.RESET}\nREMEMBER: ALWAYS KEEP BACKUPS. ALWAYS.\n")


if __name__ == "__main__":
    main()
