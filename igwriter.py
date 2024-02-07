import argparse
import json
import os
from pathlib import Path
import exiftool
from datetime import datetime
import os
import time

et = exiftool.ExifTool()

posts_json_path = "your_instagram_activity/content/posts_1.json" # Does this number increment?
stories_json_path = "your_instagram_activity/content/stories.json"

# Process the posts and stories images from the Instagram archive
def process_images(archive_path):
    
    # Ensure archive directory exists
    try:
      ensure_directory_exists(archive_path)
      print(f"Directory '{archive_path}' exists.")
    except FileNotFoundError as e:
      # Handle the case where the directory doesn't exist
      print("Error: Directory not found. Exiting...")
      exit(0)

    # Load the JSON metadata
    with open(archive_path + "/" + posts_json_path, 'r') as file:
        data = json.load(file)
    
    # Loop through media elements in the JSON file
    for item in data:
      media = item['media'][0]
      
      image_path = archive_path + "/" + media['uri']
      timestamp = exif_timestamp(item['media'][0]['creation_timestamp'])
      file_timestamp = os_timestamp(item['media'][0]['creation_timestamp'])
      title = sanitize(media['title'])

      # Set the file's modification and access time
      print(image_path)
      os.utime(image_path, (file_timestamp, file_timestamp))

      metadata = media['media_metadata']
      photo_metadata = metadata.get('photo_metadata')
      video_metadata = metadata.get('video_metadata')

      exif_data = {}
      if photo_metadata:
        exif_data = photo_metadata['exif_data'][0]
      if video_metadata:
        exif_data = video_metadata['exif_data'][0]

      latitude, lat_ref = latitude_exif(exif_data.get('latitude'))
      longitude, lon_ref = longitude_exif(exif_data.get('longitude'))

      exif = { 
        'EXIF:DateTimeOriginal': timestamp, 
        'EXIF:CreateDate': timestamp, 
        'EXIF:ImageDescription': title
      }
      if latitude and longitude:
        exif['EXIF:GPSLatitude'] = latitude
        exif['EXIF:GPSLatitudeRef'] = lat_ref
        exif['EXIF:GPSLongitude'] = longitude
        exif['EXIF:GPSLongitudeRef'] = lon_ref
      else:
        exif['EXIF:GPSLatitude'] = ''
        exif['EXIF:GPSLatitudeRef'] = ''
        exif['EXIF:GPSLongitude'] = ''
        exif['EXIF:GPSLongitudeRef'] = ''

      add_exif_data(image_path, exif)

      print(f">>> { image_path }")

def add_exif_data(image_path, exif_data):
    with exiftool.ExifTool() as et:
      et.execute(*[f"-{tag}={value}" for tag, value in exif_data.items()], image_path)

def exif_timestamp(json_timestamp):
  date_object = datetime.utcfromtimestamp(json_timestamp)
  return date_object.strftime("%Y:%m:%d %H:%M:%S")

def os_timestamp(json_timestamp):
  date_object = datetime.utcfromtimestamp(json_timestamp)
  return time.mktime(date_object.timetuple())

def latitude_exif(lat):
  if lat is None:
      return None, None
  ref = 'S' if lat < 0 else 'N'
  return abs(lat), ref

def longitude_exif(lon):
  if lon is None:
      return None, None
  ref = 'W' if lon < 0 else 'E'
  return abs(lon), ref

def ensure_directory_exists(directory_path):
    path = Path(directory_path)
    if not path.is_dir():
        # If the path doesn't exist or isn't a directory, raise an error
        raise FileNotFoundError(f"The directory '{directory_path}' does not exist.")
    
def sanitize(caption, max_length=255):
    # Replace double quotes with single quotes (or remove them)
    sanitized = caption.replace('"', "'")
    # Truncate to max_length to ensure it fits in EXIF limitations
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized

# Main: 
def main():
    parser = argparse.ArgumentParser(description="Embed Instagram metadata as EXIF data into image files.")
    parser.add_argument('-a', '--archive', type=str, help="Path to downloaded archive of Instagram account data from Meta.")

    args = parser.parse_args()

    process_images(args.archive)

if __name__ == "__main__":
    main()