# このスクリプトをEXE形式に変換するには、以下のコマンドを使用してください:
# pyinstaller --onefile --noconsole box_photo_geo_url.py --hidden-import=boxsdk.object.recent_item
# 必要に応じて --add-data オプションでconfig.json等を同梱してください。
# boxsdkのrecent_itemエラー対策として --hidden-import=boxsdk.object.recent_item を追加しています。

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
import tkinter as tk
from tkinter import simpledialog
import sys  # 追加

# config.jsonから認証情報を読み込む
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'config.json')  # 修正
    if not os.path.exists(config_path):
        # ファイルがなければ空のファイルを作成
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('{}')
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    config_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'config.json')  # 修正
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_credentials_gui(initial_access_token=None, initial_folder_url=None):
    # 1画面でaccess_tokenとfolder_urlを入力
    import tkinter as tk
    from tkinter import simpledialog

    class CredentialsDialog(simpledialog.Dialog):
        def body(self, master):
            tk.Label(master, text="開発者トークン:").grid(row=0, sticky="e")
            tk.Label(master, text="フォルダURL:").grid(row=1, sticky="e")
            self.token_entry = tk.Entry(master, width=60)
            self.token_entry.insert(0, initial_access_token or "")
            self.token_entry.grid(row=0, column=1)
            self.folder_entry = tk.Entry(master, width=60)
            self.folder_entry.insert(0, initial_folder_url or "")
            self.folder_entry.grid(row=1, column=1)
            return self.token_entry

        def apply(self):
            self.result = (
                self.token_entry.get(),
                self.folder_entry.get()
            )

    root = tk.Tk()
    root.withdraw()
    dialog = CredentialsDialog(root, title="Box 認証情報入力")
    root.destroy()
    if dialog.result:
        return dialog.result
    else:
        return None, None

def extract_folder_id_from_url(folder_url):
    """
    URLからfolder_id部分のみ抽出（例: https://app.box.com/folder/319478787863 → 319478787863）
    """
    import re
    if not folder_url:
        return ""
    m = re.search(r'/folder/(\d+)', folder_url)
    return m.group(1) if m else folder_url

def get_box_client(access_token):
    oauth2 = OAuth2(
        client_id=None,
        client_secret=None,
        access_token=access_token,
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

def show_results_gui(results_text):
    import tkinter as tk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Box Photo GeoURL 結果")
    text = ScrolledText(root, width=120, height=40, font=("Meiryo", 10))
    text.pack(fill="both", expand=True)
    text.insert("end", results_text)
    text.config(state="disabled")
    tk.Button(root, text="閉じる", command=root.destroy).pack(pady=5)
    root.mainloop()

def main():
    config = load_config()
    # 1画面でaccess_tokenとfolder_urlを入力
    access_token, folder_url = get_credentials_gui(
        initial_access_token=config.get("access_token", ""),
        initial_folder_url=config.get("folder_id", "")
    )
    folder_id = extract_folder_id_from_url(folder_url)
    # 入力値をconfig.jsonに保存（folder_idはURL形式で保存）
    config["folder_id"] = folder_url
    config["access_token"] = access_token
    save_config(config)
    client = get_box_client(access_token)
    # 再帰的に画像ファイルとパスを取得
    image_files = get_image_files_from_folder_recursive(client, folder_id)
    result = []
    results_text = ""
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
        results_text += f"{full_name}, {lat}, {lon}, {date_taken}, {url}\n"

    # 結果を表示
    print(results_text, end="")

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
        gdf.to_file("box_photos.gpkg", driver="GPKG")
        results_text += "GPKGファイル(box_photos.gpkg)を作成しました。\n"
        results_text += "QGISで「url」列を使ってアクションやHTMLポップアップで写真を表示できます。\n"
        print("GPKGファイル(box_photos.gpkg)を作成しました。")
        print("QGISで「url」列を使ってアクションやHTMLポップアップで写真を表示できます。")
    else:
        results_text += "位置情報付き画像がありません。\n"
        print("位置情報付き画像がありません。")

    # CSVファイル作成
    if result:
        df = pd.DataFrame(result)
        df.to_csv("box_photos.csv", index=False, encoding="utf-8")
        results_text += "CSVファイル(box_photos.csv)を作成しました。\n"
        print("CSVファイル(box_photos.csv)を作成しました。")

    # GUIで結果表示
    show_results_gui(results_text)

if __name__ == '__main__': 
    main()
