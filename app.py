import streamlit as st
import os
from ftplib import FTP
from bs4 import BeautifulSoup
from datetime import datetime

# ページの設定
st.set_page_config(page_title="アークフィールド 価格表更新ツール", page_icon="📦")

st.title("📦 商品価格・画像更新ツール")
st.write("FTP経由でサーバーの注文ページを安全に更新します。")

# --- 設定情報 ---
FTP_HOST = "ftp.arkf.jp"
FTP_USER = "info@arkf.jp"

# 【修正】サーバー上のパス（ログイン直後の位置からの相対パス）
REMOTE_HTML_PATH = "cyumon/index.html"
LOCAL_HTML_PATH = "index.html"
# ----------------

with st.container():
    st.subheader("1. 認証情報")
    ftp_pass = st.text_input("FTPパスワードを入力してください", type="password")

st.markdown("---")

st.subheader("2. サーバーの接続確認・ファイル一覧の取得")
st.info("「接続テスト」を押すと、現在のFTP上の位置とファイル一覧を確認できます（パスが正しいか確認用です）。")

if st.button("🔍 サーバーの接続テスト（ファイル一覧を確認）"):
    if not ftp_pass:
        st.error("⚠️ FTPパスワードを入力してください。")
    else:
        try:
            with st.spinner("サーバーに接続中..."):
                ftp = FTP(FTP_HOST)
                ftp.login(FTP_USER, ftp_pass)
                
                # 現在のディレクトリとファイル一覧を取得
                current_dir = ftp.pwd()
                files = []
                ftp.dir(files.append)
                
                ftp.quit()
                
                st.success(f"✅ 接続成功！現在の場所: `{current_dir}`")
                st.write("📁 **現在のフォルダの中身:**")
                for f in files:
                    st.code(f)
        except Exception as e:
            st.error(f"❌ 接続エラー: {e}")

st.markdown("---")

st.subheader("3. 価格表の更新実行")
if st.button("🚀 価格表の更新を今すぐ実行する", type="primary"):
    if not ftp_pass:
        st.error("⚠️ FTPパスワードを入力してください。")
    else:
        with st.spinner("処理を実行中... しばらくお待ちください。"):
            status_box = st.empty()
            
            try:
                # 1. FTP接続
                status_box.text("🔌 FTPサーバーに接続中...")
                ftp = FTP(FTP_HOST)
                ftp.login(FTP_USER, ftp_pass)

                # 2. HTMLのダウンロード
                status_box.text(f"📥 サーバーからHTML ({REMOTE_HTML_PATH}) をダウンロード中...")
                with open(LOCAL_HTML_PATH, "wb") as f:
                    ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)

                # 3. HTMLの解析と更新
                status_box.text("✍️ HTMLの内容を更新中...")
                with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")

                # 価格表更新日の自動日付更新
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