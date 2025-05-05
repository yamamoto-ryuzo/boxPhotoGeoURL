# pip install boxsdk requests Pillow exifread geopandas shapely pandas pillow-heif
# Boxのフォルダ内の画像ファイルを取得し、EXIF情報から緯度経度を取得して共有リンクを表示するスクリプト
# 画像のExif情報（位置情報）は画像ファイル自体に埋め込まれているため、**画像をダウンロードせずにExif情報を取得することはできません**。  
# Box APIも画像のメタデータとしてExif情報を直接返すエンドポイントは提供していません。

import os
import json
from boxsdk import Client, OAuth2
import requests
from PIL import Image
import exifread
from io import BytesIO
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd

# config.jsonから認証情報を読み込む
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    # ファイル内容をそのままjson.loadsせず、json.loadでパース（改行や制御文字の除去は不要）
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
    # Exif座標情報が取得できる主な画像拡張子（.heicも含める）
    image_exts = ('.jpg', '.jpeg', '.tif', '.tiff', '.heic')
    folder = client.folder(folder_id).get()
    items = folder.get_items()
    image_files = []
    for item in items:
        if item.type == 'file' and item.name.lower().endswith(image_exts):
            image_files.append(item)
    return image_files

def get_image_files_from_folder_recursive(client, folder_id, parent_path=""):
    """指定フォルダ以下すべての画像ファイルを再帰的に取得し、パス情報も付与"""
    image_exts = ('.jpg', '.jpeg', '.tif', '.tiff', '.heic')
    image_files = []
    folder = client.folder(folder_id).get()
    current_path = os.path.join(parent_path, folder.name) if parent_path else folder.name
    items = folder.get_items()
    for item in items:
        if item.type == 'file' and item.name.lower().endswith(image_exts):
            # ファイルとそのパスをタプルで返す
            image_files.append((item, current_path))
        elif item.type == 'folder':
            image_files.extend(get_image_files_from_folder_recursive(client, item.id, current_path))
    return image_files

def get_exif_location(image_bytes):
    try:
        tags = exifread.process_file(BytesIO(image_bytes))
    except Exception:
        # .heicの場合はpillow-heifで対応
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            img = Image.open(BytesIO(image_bytes))
            exif = img.getexif()
            # PillowのExifはdict型
            gps_info = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
            if gps_info:
                def _convert_to_degrees_pillow(value):
                    d, m, s = value
                    return float(d[0]) / d[1] + float(m[0]) / m[1] / 60 + float(s[0]) / s[1] / 3600
                lat = _convert_to_degrees_pillow(gps_info[2])
                if gps_info[1] != 'N':
                    lat = -lat
                lon = _convert_to_degrees_pillow(gps_info[4])
                if gps_info[3] != 'E':
                    lon = -lon
                return lat, lon
            else:
                return None, None
        except Exception:
            return None, None
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

def get_exif_location_and_datetime(image_bytes):
    # 緯度・経度・撮影日を取得
    date_taken = None
    try:
        tags = exifread.process_file(BytesIO(image_bytes))
    except Exception:
        # .heicの場合はpillow-heifで対応
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            img = Image.open(BytesIO(image_bytes))
            exif = img.getexif()
            gps_info = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
            date_taken = exif.get(0x9003) if exif else None  # DateTimeOriginal
            if gps_info:
                def _convert_to_degrees_pillow(value):
                    d, m, s = value
                    return float(d[0]) / d[1] + float(m[0]) / m[1] / 60 + float(s[0]) / s[1] / 3600
                lat = _convert_to_degrees_pillow(gps_info[2])
                if gps_info[1] != 'N':
                    lat = -lat
                lon = _convert_to_degrees_pillow(gps_info[4])
                if gps_info[3] != 'E':
                    lon = -lon
                return lat, lon, str(date_taken) if date_taken else None
            else:
                return None, None, None
        except Exception:
            return None, None, None
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
        # 撮影日を取得（DateTimeOriginalまたはDateTime）
        date_taken = str(tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime') or "")
        return lat, lon, date_taken if date_taken else None
    except Exception:
        return None, None, None

def get_shared_link(client, file):
    # 共有リンクの自動作成はしていません
    try:
        shared_link = file.get_shared_link()  # 既存の共有リンクのみ取得
    except Exception:
        shared_link = ""
    return shared_link

# 401エラー（invalid_token）の主な原因と対策
# - アクセストークンが無効、期限切れ、または間違っている
# - config.jsonのaccess_tokenが古い/正しく発行されていない
# - リフレッシュトークンがない場合、トークンの自動更新もできない

# 対策:
# 1. BoxのOAuth2認証フローで新しいaccess_tokenを取得し、config.jsonを更新してください
# 2. 長期運用する場合はrefresh_tokenも保存し、トークンの自動更新処理を実装してください
# 3. 認証情報（client_id, client_secret, access_token）が正しいか再確認してください

# 参考: https://developer.box.com/guides/authentication/oauth2/

# 401エラー（invalid_token）・refresh_tokenエラーの解説
# - access_tokenが無効または期限切れです。
# - また、refresh_tokenがないためトークンの自動更新もできません。
# 
# 対策:
# 1. BoxのOAuth2認証フローを再実行し、新しいaccess_token（必要ならrefresh_tokenも）を取得してください。
# 2. config.jsonのaccess_tokenを新しいものに書き換えてください。
# 3. 長期運用する場合はrefresh_tokenも保存し、トークンの自動更新処理を実装してください。
# 
# 参考: https://developer.box.com/guides/authentication/oauth2/
# 
# ※ access_tokenは有効期限が短いため、定期的な更新が必要です。

# 写真データ（Exif情報）からはEPSGコードは取得できません。
# 理由:
# - ExifのGPS情報は緯度(latitude)・経度(longitude)のみで、測地系や投影法（EPSGコード）は含まれていません。
# - 一般的なカメラやスマートフォンのExif GPS情報はWGS84（EPSG:4326）を前提としています。
# - そのため、プログラムではEPSG:4326を指定しています。

def main():
    config = load_config()
    folder_id = config["folder_id"]  # config.jsonから取得
    client = get_box_client()
    # 再帰的に画像ファイルとパスを取得
    image_files = get_image_files_from_folder_recursive(client, folder_id)
    result = []
    for file, folder_path in image_files:
        try:
            image_bytes = client.file(file.id).content()
        except Exception:
            image_bytes = None
        lat, lon, date_taken = get_exif_location_and_datetime(image_bytes) if image_bytes else (None, None, None)
        url = f"https://app.box.com/file/{file.id}"
        # フォルダ階層を含めたファイル名を作成
        full_name = os.path.join(folder_path, file.name)
        result.append({
            'name': file.name,
            'full_name': full_name,
            'latitude': lat,
            'longitude': lon,
            'date_taken': date_taken,
            'url': url
        })
    # 結果を表示
    for r in result:
        print(f"{r['full_name']}, {r['latitude']}, {r['longitude']}, {r['date_taken']}, {r['url']}")

    # GPKGデータ作成
    records = [
        {
            "name": r["name"],
            "full_name": r["full_name"],
            "url": r["url"],
            "date_taken": r["date_taken"],
            "geometry": Point(r["longitude"], r["latitude"])
        }
        for r in result if r["latitude"] is not None and r["longitude"] is not None
    ]
    if records:
        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        # QGISで写真の連続再生（ポップアップやアタッチメント）を行うには
        # 1. "url"列にWeb上で直接アクセスできる画像URLを格納する
        # 2. QGISで「アクション」や「HTMLポップアップ」機能を使い、url列を画像表示に利用する
        # 例: QGISの「アクション」に `[% "url" %]` を設定し、Webブラウザで画像を開く
        # 例: QGISの「HTMLポップアップ」に <img src="[% "url" %]" width="400"> などを記述
        gdf.to_file("box_photos.gpkg", driver="GPKG")
        print("GPKGファイル(box_photos.gpkg)を作成しました。")
        print("QGISで「url」列を使ってアクションやHTMLポップアップで写真を表示できます。")
    else:
        print("位置情報付き画像がありません。")

    # CSVファイル作成
    if result:
        df = pd.DataFrame(result)
        df.to_csv("box_photos.csv", index=False, encoding="utf-8")
        print("CSVファイル(box_photos.csv)を作成しました。")

if __name__ == '__main__': 
    main()
