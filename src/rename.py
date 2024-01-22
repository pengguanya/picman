from PIL import Image, ExifTags
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import os
import re
import shutil
import argparse

def handle_image_file(filename, verbose):
    try:
        with Image.open(filename) as image:
            info = image._getexif()
    except IOError:
        print("Could not read image file:", filename)
        return None

    if info is not None:
        for tag, value in info.items():
            key = ExifTags.TAGS.get(tag, tag)
            if key == 'DateTimeOriginal':
                return value.replace(":", "").replace(" ", "_")
    else:
        if verbose:
            print(f"No EXIF data found for image file: {filename}")

    return None

def handle_video_file(filename, verbose):
    parser = createParser(filename)
    with parser:
        metadata = extractMetadata(parser)

        if metadata is not None:
            for line in metadata.exportPlaintext():
                if line.startswith('- Creation date: '):
                    date_time = line[17:].replace("-", "").replace(":", "").replace(" ", "_")
                    return date_time.split(".")[0]
        else:
            if verbose:
                print(f"No metadata found for video file: {filename}")

    return None

def is_valid_format(filename):
    pattern = r'^\d{8}_\d{6}.*$'  # updated pattern to look for timestamps at the beginning of the filename followed by anything
    return re.match(pattern, filename.split('.')[0]) is not None  # consider only the filename part, not the file extension

def rename_file(path, filename, new_name, overwrite, output, verbose):
    old_file_path = os.path.join(path, filename)
    new_dir = os.path.expanduser(output)
    new_file_path = os.path.join(new_dir, new_name)
    if not os.path.exists(old_file_path):
        print(f"Source file does not exist: {old_file_path}")
        return
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    if not overwrite and os.path.exists(new_file_path):
        i = 1
        filename, extension = os.path.splitext(new_name)
        while os.path.exists(os.path.join(new_dir, f"{filename}_{i}{extension}")):
            i += 1
        new_name = f"{filename}_{i}{extension}"
        new_file_path = os.path.join(new_dir, new_name)
    try:
        shutil.move(old_file_path, new_file_path)
        if verbose:
            print(f"Renamed file {old_file_path} to {new_file_path}")
    except Exception as e:
        print(f"Could not rename file: {old_file_path} - {str(e)}")

def log_unsupported_format(filename, extension, verbose):
    if verbose:
        print(f'Skipped file {filename}. Unsupported file format: {extension}')

def process_files(path, overwrite=False, output=None, recursive=True, verbose=False):
    path = os.path.expanduser(path) 
    if output is None:
        base_output_dir = path
    else:
        base_output_dir = os.path.expanduser(output)  

    for dirpath, dirnames, filenames in os.walk(path):
        if not recursive and dirpath != path:
            break;

        # Update output directory for each subdirectory
        relative_dir = os.path.relpath(dirpath, path)        
        output_dir = os.path.join(base_output_dir, relative_dir)

        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov')):
                date_taken = None
                full_path = os.path.join(dirpath, filename)
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    date_taken = handle_image_file(full_path, verbose)
                elif filename.lower().endswith(('.mp4', '.mov')):
                    date_taken = handle_video_file(full_path, verbose)

                if date_taken is not None and not is_valid_format(filename):
                    new_name = date_taken + os.path.splitext(filename)[1]
                    rename_file(dirpath, filename, new_name, overwrite, output_dir, verbose)
                elif verbose:
                    print(f'Skipped file {filename}. Date taken: {date_taken}. Name already in YYYYMMDD_HHMMSS format: {is_valid_format(filename)}')

            else:
                filename, extension = os.path.splitext(filename.lower())
                log_unsupported_format(filename, extension, verbose)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Renames photo or media files under a given folder to their date taken.")
    parser.add_argument("path", help="path of the directory")
    parser.add_argument("-w", "--overwrite", help="overwrite the files with same timestamp name", action="store_true")
    parser.add_argument("-o", "--output", help="path to output the renamed images", default=None)
    parser.add_argument("-r", "--recursive", help="apply rename job recursively on directories", action="store_true")
    parser.add_argument("-v", "--verbose", help="print more detailed messages", action="store_true")

    args = parser.parse_args()

    process_files(args.path, args.overwrite, args.output, args.recursive, args.verbose)
