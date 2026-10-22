import streamlit as st
import os
from ftplib import FTP
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re

# ページのレイアウト設定（広めの画面にします）
st.set_page_config(page_title="アークフィールド 価格表更新ツール", page_icon="📦", layout="wide")

st.title("📦 商品価格・画像一括更新ツール")
st.write("FTPから注文ページのHTMLを読み込み、商品名・価格・備考・画像の編集を行ってサーバーに反映します。")

# --- 設定情報 ---
FTP_HOST = "ftp.arkf.jp"
FTP_USER = "info@arkf.jp"
REMOTE_HTML_PATH = "cyumon/index.html"
LOCAL_HTML_PATH = "index.html"
# ----------------

# セッションステートの初期化
if "products" not in st.session_state:
    st.session_state.products = None
if "image_updates" not in st.session_state:
    st.session_state.image_updates = {}

# サイドバー：接続とデータ読み込み
with st.sidebar:
    st.header("🔑 1. 接続 & データ読込")
    ftp_pass = st.text_input("FTPパスワード", type="password")
    
    if st.button("📥 サーバーから商品データを取得", type="primary"):
        if not ftp_pass:
            st.error("⚠️ パスワードを入力してください。")
        else:
            try:
                with st.spinner("サーバーからHTMLをダウンロード中..."):
                    ftp = FTP(FTP_HOST)
                    ftp.login(FTP_USER, ftp_pass)
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)
                    ftp.quit()
                
                # HTMLを解析して商品リストを抽出
                with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                
                products = []
                for idx, tr in enumerate(soup.find_all("tr")):
                    name_div = tr.find(class_="product-name")
                    if not name_div:
                        continue
                    
                    p_name = name_div.text.strip()
                    
                    lot_div = tr.find(class_="product-lot")
                    p_lot = lot_div.text.replace("ロット:", "").strip() if lot_div else ""
                    
                    price_td = tr.find(class_="price-col")
                    p_price = price_td.text.strip() if price_td else ""
                    
                    note_td = tr.find(class_="note-col")
                    p_note = note_td.text.strip() if note_td else ""
                    
                    img_col = tr.find(class_="img-col")
                    has_img = "No Image" not in img_col.text if img_col else False
                    
                    products.append({
                        "id": idx,
                        "商品名": p_name,
                        "ロット": p_lot,
                        "価格": p_price,
                        "備考": p_note,
                        "画像状態": "画像あり" if has_img else "No Image"
                    })
                
                st.session_state.products = products
                st.success(f"✅ {len(products)}件の商品データを読み込みました！")
            except Exception as e:
                st.error(f"❌ エラー: {e}")

# メイン画面：データが読み込まれたら編集UIを表示
if st.session_state.products is None:
    st.info("👈 まず左側のサイドバーにFTPパスワードを入力し、「サーバーから商品データを取得」ボタンを押してください。")
else:
    st.markdown("---")
    st.subheader("📝 2. 商品情報の編集（商品名・ロット・価格・備考）")
    st.write("下の表の中の文字を直接書き換えることで、内容を自由に変更できます。")
    
    # 表形式で編集できるUI
    df = pd.DataFrame(st.session_state.products)
    edited_df = st.data_editor(
        df,
        column_config={
            "id": None, # ID列は非表示
            "画像状態": st.column_config.TextColumn("画像状態", disabled=True),
            "商品名": st.column_config.TextColumn("商品名", width="medium"),
            "ロット": st.column_config.TextColumn("ロット", width="small"),
            "価格": st.column_config.TextColumn("価格", width="small"),
            "備考": st.column_config.TextColumn("備考", width="small"),
        },
        hide_index=True,
        num_rows="fixed",
        use_container_width=True,
        key="product_editor"
    )
    
    st.markdown("---")
    st.subheader("🖼️ 3. 写真（画像）の入れ替え・追加")
    st.write("写真を入れ替えたい商品を選び、新しい画像ファイル（jpg / png）をアップロードしてください。")
    
    product_names = edited_df["商品名"].tolist()
    selected_product = st.selectbox("写真を変更する商品を選択", product_names)
    
    uploaded_image = st.file_uploader("新しい画像を選択", type=["jpg", "jpeg", "png"])
    
    if uploaded_image is not None:
        st.image(uploaded_image, width=150, caption=f"選択中: {selected_product}")
        if st.button("この画像をセットする"):
            st.session_state.image_updates[selected_product] = uploaded_image
            st.success(f"「{selected_product}」の画像を変更リストに登録しました。")

    # セットされている画像の一覧と解除
    if st.session_state.image_updates:
        st.write("📌 **変更予定の画像:**")
        for p_name in list(st.session_state.image_updates.keys()):
            col1, col2 = st.columns([4, 1])
            col1.text(f"・ {p_name}")
            if col2.button("解除", key=f"del_{p_name}"):
                del st.session_state.image_updates[p_name]
                st.rerun()

    st.markdown("---")
    st.subheader("🚀 4. サーバーへの反映")
    st.info("編集と画像のセットが終わったら、下のボタンを押すと一括でサーバーが更新されます。")
    
    if st.button("変更を保存してサーバー（FTP）に反映する", type="primary"):
        if not ftp_pass:
            st.error("⚠️ 左側のサイドバーにFTPパスワードを入力してください。")
        else:
            with st.spinner("サーバーのHTMLを更新し、画像をアップロード中..."):
                try:
                    ftp = FTP(FTP_HOST)
                    ftp.login(FTP_USER, ftp_pass)
                    
                    # 1. サーバーから最新のHTMLを再度ダウンロードしてベースにする
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)
                    
                    with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")
                    
                    # 更新日の自動書き換え
                    today_str = datetime.now().strftime("価格表更新日：%Y年%m月%d日")
                    date_element = soup.find(class_="update-date")
                    if date_element:
                        date_element.string = today_str
                    
                    # 2. 表で編集されたテキスト情報をHTMLに反映
                    for index, row in edited_df.iterrows():
                        target_name_original = st.session_state.products[index]["商品名"]
                        
                        for tr in soup.find_all("tr"):
                            name_div = tr.find(class_="product-name")
                            if name_div and name_div.text.strip() == target_name_original.strip():
                                # 商品名
                                name_div.string = row["商品名"]
                                
                                # ロット
                                lot_div = tr.find(class_="product-lot")
                                if lot_div:
                                    lot_div.string = f"ロット: {row['ロット']}"
                                
                                # 価格
                                price_td = tr.find(class_="price-col")
                                if price_td:
                                    price_td.string = row["価格"]
                                
                                # 備考
                                note_td = tr.find(class_="note-col")
                                if note_td:
                                    note_td.string = row["備考"]
                                
                                # input要素のデータ属性も連動
                                qty_input = tr.find(class_="qty-input")
                                if qty_input:
                                    qty_input["data-name"] = row["商品名"]
                                    qty_input["data-lot"] = row["ロット"]
                                    qty_input["data-price"] = row["価格"]
                                    qty_input["name"] = row["商品名"]
                                
                                break

                    # 3. 画像のアップロードとHTML書き換え
                    for p_name, img_file in st.session_state.image_updates.items():
                        safe_name = re.sub(r'[^\w\-_]', '_', p_name)
                        img_filename = f"{safe_name}.jpg"
                        remote_img_path = f"cyumon/images/{img_filename}"
                        
                        temp_img_path = f"temp_{img_filename}"
                        with open(temp_img_path, "wb") as f:
                            f.write(img_file.getbuffer())
                        
                        # 画像をFTPアップロード
                        with open(temp_img_path, "rb") as f:
                            ftp.storbinary(f"STOR {remote_img_path}", f)
                        
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)
                        
                        # HTML側の<img>タグを更新
                        for tr in soup.find_all("tr"):
                            name_div = tr.find(class_="product-name")
                            if name_div and name_div.text.strip() == p_name.strip():
                                img_col = tr.find(class_="img-col")
                                if img_col:
                                    img_col.clear()
                                    new_img = soup.new_tag("img", src=f"./images/{img_filename}")
                                    img_col.append(new_img)
                                break

                    # ローカルHTMLに保存してアップロード
                    with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                    
                    with open(LOCAL_HTML_PATH, "rb") as f:
                        ftp.storbinary(f"STOR {REMOTE_HTML_PATH}", f)
                    
                    ftp.quit()
                    st.success("🎉 すべての変更がサーバーに正常に反映されました！")
                    
                except Exception as e:
                    st.error(f"❌ 更新中にエラーが発生しました: {e}")