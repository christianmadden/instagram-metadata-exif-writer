import argparse
import json
from pathlib import Path
import exiftool
from datetime import datetime
import os
import time

# Ensure only one instance of ExifTool is used to improve efficiency
et = exiftool.ExifTool()
et.start()

# Paths to the JSON files within the Instagram archive
posts_json_path = "your_instagram_activity/content/posts_1.json"  # Placeholder path; adapt as necessary
stories_json_path = "your_instagram_activity/content/stories.json"  # Currently unused but included for future expansion

def process_images(archive_path):
    """
    Processes images from an Instagram archive by embedding metadata into the image files.
    """
    # Validate the archive directory
    if not ensure_directory_exists(archive_path):
        print(f"Error: Directory '{archive_path}' not found. Exiting...")
        return

    # Load and process posts JSON
    try:
        with open(Path(archive_path) / posts_json_path, 'r') as file:
            posts_data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{posts_json_path}' not found in the archive. Exiting...")
        return

    # Process each post in the JSON data
    for item in posts_data:
        process_media_item(item, archive_path)

def process_media_item(item, archive_path):
    """
    Processes a single media item, embedding EXIF data into the corresponding image file.
    """
    media = item['media'][0]
    image_path = Path(archive_path) / media['uri']
    timestamp = exif_timestamp(media['creation_timestamp'])
    file_timestamp = os_timestamp(media['creation_timestamp'])
    title = sanitize(media.get('title', 'Instagram Post'))

    # Set the file's modification and access times
    os.utime(image_path, (file_timestamp, file_timestamp))

    # Prepare EXIF data
    exif_data = prepare_exif_data(media, timestamp, title)

    # Embed EXIF data into the image
    add_exif_data(image_path, exif_data)
    print(f"Processed image: {image_path}")

def prepare_exif_data(media, timestamp, title):
    """
    Prepares EXIF data from media metadata.
    """
    metadata = media['media_metadata']
    photo_metadata = metadata.get('photo_metadata')
    video_metadata = metadata.get('video_metadata')

    exif_data = {
        'EXIF:DateTimeOriginal': timestamp,
        'EXIF:CreateDate': timestamp,
        'EXIF:ImageDescription': title
    }

    if photo_metadata:
        exif_data.update(photo_metadata['exif_data'][0])
    if video_metadata:
        exif_data.update(video_metadata['exif_data'][0])

    # Include GPS data if available
    latitude, lat_ref = latitude_exif(exif_data.get('latitude'))
    longitude, lon_ref = longitude_exif(exif_data.get('longitude'))
    if latitude and longitude:
        exif_data.update({
            'EXIF:GPSLatitude': latitude,
            'EXIF:GPSLatitudeRef': lat_ref,
            'EXIF:GPSLongitude': longitude,
            'EXIF:GPSLongitudeRef': lon_ref
        })

    return exif_data

def add_exif_data(image_path, exif_data):
    """
    Embeds EXIF data into an image file using ExifTool.
    """
    commands = [f"-{tag}={value}" for tag, value in exif_data.items() if value]
    et.execute(*commands, str(image_path))

def exif_timestamp(json_timestamp):
    """
    Converts a timestamp from JSON into an EXIF-compatible string format.
    """
    date_object = datetime.utcfromtimestamp(json_timestamp)
    return date_object.strftime("%Y:%m:%d %H:%M:%S")

def os_timestamp(json_timestamp):
    """
    Converts a JSON timestamp into a format suitable for os.utime.
    """
    date_object = datetime.utcfromtimestamp(json_timestamp)
    return time.mktime(date_object.timetuple())

def latitude_exif(lat):
    """
    Formats latitude for EXIF data, including reference (N/S).
    """
    if lat is None:
        return None, None
    ref = 'S' if lat < 0 else 'N'
    return abs(lat), ref

def longitude_exif(lon):
    """
    Formats longitude for EXIF data, including reference (W/E).
    """
    if lon is None:
        return None, None
    ref = 'W' if lon < 0 else 'E'
    return abs(lon), ref

def ensure_directory_exists(directory_path):
    """
    Checks if the specified directory exists.
    """
    path = Path(directory_path)
    return path.is_dir()

def sanitize(caption, max_length=255):
    """
    Sanitizes a caption to be compatible with EXIF specifications.
    """
    sanitized = caption.replace('"', "'")[:max_length]
    return sanitized

def main():
    """
    Main function to parse arguments and process the Instagram archive.
    """
    parser = argparse.ArgumentParser(description="Embed Instagram metadata as EXIF data into image files.")
    parser.add_argument('-a', '--archive', required=True, type=str, help="Path to downloaded archive of Instagram account data from Meta.")
    args = parser.parse_args()

    process_images(args.archive)

if __name__ == "__main__":
    main()
