import streamlit as st
import os
from ftplib import FTP
from bs4 import BeautifulSoup
from datetime import datetime

# ページの設定
st.set_page_config(page_title="アークフィールド 価格表更新ツール", page_icon="📦")

st.title("📦 商品価格・画像更新ツール")
st.write("FTP経由でサーバーの注文ページ（`index.html`）を安全に更新します。")

# --- 設定情報 ---
FTP_HOST = "ftp.arkf.jp"
FTP_USER = "info@arkf.jp"
REMOTE_HTML_PATH = "/www.arkf.jp/cyumon/index.html"
LOCAL_HTML_PATH = "index.html"
# ----------------

with st.container():
    st.subheader("1. 認証情報")
    # パスワード入力（伏字になります）
    ftp_pass = st.text_input("FTPパスワードを入力してください", type="password")

st.markdown("---")

st.subheader("2. 更新の実行")
st.info("下のボタンを押すと、サーバーから最新のHTMLを読み込んで更新・アップロードを実行します。")

# ボタンを押したときだけ処理が走る（これで「くるくる」フリーズを防げます）
if st.button("🚀 価格表の更新を今すぐ実行する", type="primary"):
    if not ftp_pass:
        st.error("⚠️ FTPパスワードを入力してください。")
    else:
        # 処理中のグルグル表示とメッセージ
        with st.spinner("処理を実行中... しばらくお待ちください。"):
            status_box = st.empty()
            
            try:
                # 1. FTP接続
                status_box.text("🔌 FTPサーバーに接続中...")
                ftp = FTP(FTP_HOST)
                ftp.login(FTP_USER, ftp_pass)

                # 2. HTMLのダウンロード
                status_box.text("📥 サーバーからHTMLファイルをダウンロード中...")
                with open(LOCAL_HTML_PATH, "wb") as f:
                    ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)

                # 3. HTMLの解析と更新
                status_box.text("✍️ HTMLの内容を更新中...")
                with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")

                # 例：価格表更新日の自動日付更新
                today_str = datetime.now().strftime("価格表更新日：%Y年%m月%d日")
                date_element = soup.find(class_="update-date")
                if date_element:
                    date_element.string = today_str

                # 変更をローカルに保存
                with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
                    f.write(str(soup))

                # 4. アップロード
                status_box.text("📤 更新したHTMLをサーバーにアップロード中...")
                with open(LOCAL_HTML_PATH, "rb") as f:
                    ftp.storbinary(f"STOR {REMOTE_HTML_PATH}", f)

                ftp.quit()
                
                status_box.empty()
                st.success("🎉 すべての更新とアップロードが完了しました！")

            except Exception as e:
                status_box.empty()
                st.error(f"❌ エラーが発生しました: {e}")