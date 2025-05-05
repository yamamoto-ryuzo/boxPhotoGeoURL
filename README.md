# Boxフォルダ写真位置情報抽出アプリ

## 概要
このアプリは、Boxクラウドストレージ内の指定フォルダ（サブフォルダ含む）に保存された画像ファイル（JPEG, TIFF, HEICなど）を自動で取得し、各画像のExif情報から位置情報（緯度・経度）や撮影日を抽出します。  
抽出した情報は、地理空間データ（GPKG形式）およびCSVファイルとして出力され、QGIS等のGISソフトで地図上に写真を可視化できます。

## 主な機能
- Box APIを利用し、指定フォルダ以下の全画像ファイルを再帰的に取得
- 画像のExif情報から緯度・経度・撮影日を自動抽出
- 画像のBox上のURLやフォルダ階層付きファイル名も記録
- 位置情報付き画像をGPKG（GeoPackage）およびCSVで出力
- QGISでの写真連続表示やポップアップ表示に対応

## 使い方

1. 必要なPythonパッケージをインストール  
   ```
   pip install boxsdk requests Pillow exifread geopandas shapely pandas pillow-heif
   ```

2. `config.json`を作成し、BoxのAPI認証情報と対象フォルダIDを記載  
   ```json
   {
       "client_id": "YOUR_CLIENT_ID",
       "client_secret": "YOUR_CLIENT_SECRET",
       "access_token": "YOUR_ACCESS_TOKEN",
       "folder_id": "YOUR_FOLDER_ID"
   }
   ```

3. スクリプトを実行  
   ```
   python box_photo_geo_url.py
   ```

4. 実行後、`box_photos.gpkg`（地理空間データ）と`box_photos.csv`（一覧表）が作成されます。

## QGISでの活用例

- GPKGファイルをQGISに追加し、「url」列を使ってアクションやHTMLポップアップで写真を表示できます。
- 例：HTMLポップアップに `<img src="[% "url" %]" width="400">` を記述すると、地図上で写真を連続表示できます。

## 注意事項

- Boxのアクセストークンは有効期限が短いため、定期的な更新が必要です。
- 画像にExif位置情報がない場合は、出力データに緯度・経度は含まれません。
- `.heic`画像のExif取得には`pillow-heif`が必要です。

## ライセンス
MIT License
