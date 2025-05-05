# Boxフォルダ写真位置情報抽出アプリ

## 概要
このアプリは、Boxクラウドストレージ内の指定フォルダ（サブフォルダ含む）に保存された画像ファイル（JPEG, TIFF, HEICなど）を自動で取得し、各画像のExif情報から位置情報（緯度・経度）や撮影日を抽出します。  
抽出した情報は、地理空間データ（GPKG形式）およびCSVファイルとして出力され、QGIS等のGISソフトで地図上に写真を可視化できます。

## 主な機能
- Box APIを利用し、指定フォルダ以下の全画像ファイルを再帰的に取得
- 画像のExif情報から緯度・経度・撮影日を自動抽出
- 画像のBox上のURLやフォルダ階層付きファイル名も記録
- 位置情報付き画像をGPKG（GeoPackage）およびCSVで出力

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

## GitHub上での実行について

このアプリはBox APIの認証情報（client_id, client_secret, access_tokenなど）や画像ファイルのダウンロード処理を必要とするため、  
**GitHub ActionsやCodespacesなどのクラウド上で直接実行することは推奨されません**。  
理由：
- Boxのアクセストークンやクライアントシークレットなどの機密情報をGitHubリポジトリやクラウド上に置くことはセキュリティ上危険です。
- Box APIの利用にはユーザーごとの認証が必要であり、GitHub上での自動実行はBoxの利用規約やセキュリティポリシーに抵触する場合があります。
- 画像ファイルのダウンロードやGPKG/CSVの生成はローカル環境での実行を前提としています。

**必ずローカルPC上で実行してください。**

## 注意事項

- Boxのアクセストークンは有効期限が短いため、定期的な更新が必要です。
- 画像にExif位置情報がない場合は、出力データに緯度・経度は含まれません。
- `.heic`画像のExif取得には`pillow-heif`が必要です。

## ライセンス
MIT License
