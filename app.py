import os
import getpass
from ftplib import FTP
from bs4 import BeautifulSoup
from datetime import datetime

# --- 設定情報 ---
FTP_HOST = "ftp.arkf.jp"
FTP_USER = "info@arkf.jp"

# サーバー上のHTMLファイルのパス（サーバーの公開ディレクトリ構成に合わせてパス調整してください）
REMOTE_HTML_PATH = "/www.arkf.jp/cyumon/index.html" 
LOCAL_HTML_PATH = "index.html"

# --- 更新したいデータ（例） ---
# target_name: 変更前の商品名（HTML内を検索するための目印）
# 更新したい項目だけ書き換えてください。
UPDATED_PRODUCTS = [
    {
        "target_name": "ますイクラ醤油付け250ｇｐ",
        "new_name": "ますイクラ醤油付け250ｇｐ",
        "new_lot": "ｐ／250ｇ",
        "new_price": "2,500円",
        "new_note": "特売品",  # 備考の変更例
        "local_image": None, # 例: "images/ikura.jpg" (画像を入れ替える場合のみ指定)
        "remote_image": "/www.arkf.jp/cyumon/images/ikura.jpg"
    },
    {
        "target_name": "アルゼンチン赤エビ No.2（ｐ約50尾）",
        "new_name": "アルゼンチン赤エビ No.2（ｐ約50尾）",
        "new_lot": "p／2ｋ",
        "new_price": "4,100円", # 価格の変更例
        "new_note": "p単価",
        "local_image": None,
        "remote_image": ""
    },
    # 必要に応じて他の商品もここに追加していくことができます
]
# -----------------------------

def main():
    # パスワードをUIから安全に入力
    ftp_pass = getpass.getpass("FTPパスワードを入力してください: ")

    try:
        # 1. FTP接続
        print(f"\n[1/5] FTPサーバー ({FTP_HOST}) に接続中...")
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, ftp_pass)

        # 2. 現在のHTMLファイルをダウンロード
        print("[2/5] サーバーからHTMLファイルをダウンロード中...")
        with open(LOCAL_HTML_PATH, "wb") as f:
            ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)

        # 3. HTMLの読み込みとデータ更新
        print("[3/5] HTMLを解析し、商品情報を更新中...")
        with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # 価格表更新日の日付を今日の日付に自動更新する場合
        today_str = datetime.now().strftime("価格表更新日：%Y年%m月%d日")
        date_element = soup.find(class_="update-date")
        if date_element:
            date_element.string = today_str

        # 各行（商品）を走査して一致するものを更新
        for tr in soup.find_all("tr"):
            name_div = tr.find(class_="product-name")
            if not name_div:
                continue
            
            current_name = name_div.text.strip()

            # 更新リストに該当する商品があるかチェック
            for item in UPDATED_PRODUCTS:
                if current_name == item["target_name"].strip():
                    # ① 商品名・ロットの更新
                    lot_div = tr.find(class_="product-lot")
                    if lot_div:
                        lot_div.string = f"ロット: {item['new_lot']}"
                    name_div.string = item["new_name"]

                    # ② 価格の更新
                    price_td = tr.find(class_="price-col")
                    if price_td:
                        price_td.string = item["new_price"]

                    # ③ 備考の更新
                    note_td = tr.find(class_="note-col")
                    if note_td:
                        note_td.string = item["new_note"]

                    # ④ 画像の入れ替え（ローカル画像が指定されている場合）
                    if item.get("local_image") and os.path.exists(item["local_image"]):
                        print(f"  -> 画像をアップロード中: {item['local_image']}")
                        with open(item["local_image"], "rb") as img_f:
                            ftp.storbinary(f"STOR {item['remote_image']}", img_f)
                        
                        # HTML側の<img>タグを更新（なければ新規追加、あればsrcを書き換え）
                        img_col = tr.find(class_="img-col")
                        if img_col:
                            # 既存のNo Imageスパンを消してimgタグに置き換え
                            img_col.clear()
                            new_img = soup.new_tag("img", src=item["remote_image"].replace("/www.arkf.jp/cyumon/", "./"))
                            img_col.append(new_img)

                    # ⑤ inputタグの data 属性なども連動して更新
                    qty_input = tr.find(class_="qty-input")
                    if qty_input:
                        qty_input["data-name"] = item["new_name"]
                        qty_input["data-lot"] = item["new_lot"]
                        qty_input["data-price"] = item["new_price"]
                        # name属性も必要に応じて調整可能

        # 変更をローカルHTMLに保存
        with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(str(soup))

        # 4. 更新したHTMLファイルをアップロード
        print("[4/5] 更新したHTMLファイルをサーバーにアップロード中...")
        with open(LOCAL_HTML_PATH, "rb") as f:
            ftp.storbinary(f"STOR {REMOTE_HTML_PATH}", f)

        ftp.quit()
        print("\n[5/5] 🎉 すべての更新とアップロードが完了しました！")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()