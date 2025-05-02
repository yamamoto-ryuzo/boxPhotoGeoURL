import os
import json
from boxsdk import Client, OAuth2
import requests
from PIL import Image
import exifread
from io import BytesIO

# config.jsonから認証情報を読み込む
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_box_client():
    config = load_config()
    oauth2 = OAuth2(
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        access_token=config['access_token'],
    )
    client = Client(oauth2)
    return client

def get_image_files_from_folder(client, folder_id):
    folder = client.folder(folder_id).get()
    items = folder.get_items()
    image_files = []
    for item in items:
        if item.type == 'file' and item.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_files.append(item)
    return image_files

def get_exif_location(image_bytes):
    tags = exifread.process_file(BytesIO(image_bytes))
    def _convert_to_degrees(value):
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)
    try:
        lat = _convert_to_degrees(tags['GPS GPSLatitude'])
        if tags['GPS GPSLatitudeRef'].values[0] != 'N':
            lat = -lat
        lon = _convert_to_degrees(tags['GPS GPSLongitude'])
        if tags['GPS GPSLongitudeRef'].values[0] != 'E':
            lon = -lon
        return lat, lon
    except Exception:
        return None, None

def get_shared_link(client, file):
    shared_link = file.get_shared_link()
    return shared_link

def main():
    folder_id = 'YOUR_FOLDER_ID'  # ここにBOXのフォルダIDを入力
    client = get_box_client()
    image_files = get_image_files_from_folder(client, folder_id)
    result = []
    for file in image_files:
        # 画像をダウンロード
        image_bytes = file.content()
        lat, lon = get_exif_location(image_bytes)
        url = get_shared_link(client, file)
        result.append({
            'name': file.name,
            'latitude': lat,
            'longitude': lon,
            'url': url
        })
    # 結果を表示
    for r in result:
        print(f"{r['name']}, {r['latitude']}, {r['longitude']}, {r['url']}")

if __name__ == '__main__':
    main()
