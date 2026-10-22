import streamlit as st
import os
from ftplib import FTP
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
from PIL import Image

# ページのレイアウト設定
st.set_page_config(page_title="アークフィールド 価格表更新ツール", page_icon="📦", layout="wide")

st.title("📦 商品価格・画像・行一括管理ツール（画像クリック別ウィンドウ拡大対応）")
st.write("FTPから注文ページのHTMLを読み込み、商品の編集・行の追加・削除、および**画像クリックで別ウィンドウ拡大表示**する機能を組み込んでサーバーに反映します。")

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
                    
                    img_tag = img_col.find("img") if img_col else None
                    img_src = img_tag.get("src", "") if img_tag else ""
                    
                    products.append({
                        "id": idx,
                        "商品名": p_name,
                        "ロット": p_lot,
                        "価格": p_price,
                        "備考": p_note,
                        "画像状態": "画像あり" if has_img else "No Image",
                        "img_src": img_src
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
    st.subheader("📝 2. 商品情報の編集・行の追加・削除")
    st.write("表の下部にある **[+]** ボタンで新しい行を追加したり、行の左側を選択してゴミ箱アイコンで削除したりできます。")
    
    df = pd.DataFrame(st.session_state.products)
    editor_df = df[["商品名", "ロット", "価格", "備考", "画像状態"]].copy()
    
    edited_df = st.data_editor(
        editor_df,
        column_config={
            "画像状態": st.column_config.TextColumn("画像状態", disabled=True),
            "商品名": st.column_config.TextColumn("商品名", width="medium"),
            "ロット": st.column_config.TextColumn("ロット", width="small"),
            "価格": st.column_config.TextColumn("価格", width="small"),
            "備考": st.column_config.TextColumn("備考", width="small"),
        },
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        key="product_editor"
    )
    
    st.markdown("---")
    st.subheader("🖼️ 3. 写真（画像）の入れ替え・追加（自動正方形リサイズ）")
    product_names = [name for name in edited_df["商品名"].dropna().tolist() if name.strip() != ""]
    if product_names:
        selected_product = st.selectbox("写真を変更・追加する商品を選択", product_names)
        uploaded_image = st.file_uploader("新しい画像を選択", type=["jpg", "jpeg", "png"], key="img_uploader")
        
        if uploaded_image is not None:
            st.image(uploaded_image, width=150, caption=f"選択中: {selected_product}")
            if st.button("この画像をセットする"):
                st.session_state.image_updates[selected_product] = uploaded_image
                st.success(f"「{selected_product}」の画像を変更リストに登録しました。")

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
    st.info("編集・追加・削除が終わったら、下のボタンを押すと一括でサーバーが更新されます。")
    
    if st.button("変更を保存してサーバー（FTP）に反映する", type="primary"):
        if not ftp_pass:
            st.error("⚠️ 左側のサイドバーにFTPパスワードを入力してください。")
        else:
            with st.spinner("サーバーのHTMLを更新し、画像をアップロード中..."):
                try:
                    ftp = FTP(FTP_HOST)
                    ftp.login(FTP_USER, ftp_pass)
                    
                    # 1. 最新HTMLダウンロード
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)
                    
                    with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")
                    
                    # 更新日の書き換え
                    today_str = datetime.now().strftime("価格表更新日：%Y年%m月%d日")
                    date_element = soup.find(class_="update-date")
                    if date_element:
                        date_element.string = today_str
                    
                    # 2. テーブルの tbody をクリアして再構築
                    tbody = soup.find("tbody")
                    if tbody:
                        tbody.clear()
                        
                        for index, row in edited_df.iterrows():
                            p_name = str(row.get("商品名", "")).strip()
                            if not p_name:
                                continue  # 空行はスキップ
                            
                            p_lot = str(row.get("ロット", "")).strip()
                            p_price = str(row.get("価格", "")).strip()
                            p_note = str(row.get("備考", "")).strip()
                            
                            # 画像パスの決定
                            img_src = "./images/no-image.jpg"
                            has_custom_img = False
                            
                            for orig in st.session_state.products:
                                if orig["商品名"] == p_name and orig["画像状態"] == "画像あり":
                                    has_custom_img = True
                                    img_src = orig.get("img_src", "")
                                    break
                            
                            if p_name in st.session_state.image_updates:
                                safe_name = re.sub(r'[^\w\-_]', '_', p_name)
                                img_filename = f"{safe_name}.jpg"
                                img_src = f"./images/{img_filename}"
                                has_custom_img = True

                            # HTMLの各列タグを組み立て
                            new_tr = soup.new_tag("tr")
                            
                            # 画像列（★画像をクリックすると別タブで拡大表示されるように <a> タグで囲む）
                            td_img = soup.new_tag("td", attrs={"class": "img-col"})
                            if has_custom_img and img_src:
                                a_tag = soup.new_tag("a", attrs={"href": img_src, "target": "_blank", "title": "クリックして拡大表示"})
                                img_tag = soup.new_tag("img", src=img_src)
                                a_tag.append(img_tag)
                                td_img.append(a_tag)
                            else:
                                span_no_img = soup.new_tag("span", attrs={"class": "no-image"})
                                span_no_img.string = "No Image"
                                td_img.append(span_no_img)
                            new_tr.append(td_img)
                            
                            # 商品情報列
                            td_name = soup.new_tag("td", attrs={"class": "name-col"})
                            div_pname = soup.new_tag("div", attrs={"class": "product-name"})
                            div_pname.string = p_name
                            td_name.append(div_pname)
                            
                            div_plot = soup.new_tag("div", attrs={"class": "product-lot"})
                            div_plot.string = f"ロット: {p_lot}"
                            td_name.append(div_plot)
                            new_tr.append(td_name)
                            
                            # 価格列
                            td_price = soup.new_tag("td", attrs={"class": "price-col"})
                            td_price.string = p_price
                            new_tr.append(td_price)
                            
                            # 備考列
                            td_note = soup.new_tag("td", attrs={"class": "note-col"})
                            td_note.string = p_note
                            new_tr.append(td_note)
                            
                            # 注文数入力列
                            td_qty = soup.new_tag("td", attrs={"class": "qty-col"})
                            input_qty = soup.new_tag("input", attrs={
                                "type": "number",
                                "class": "qty-input",
                                "name": p_name,
                                "min": "0",
                                "value": "",
                                "placeholder": "0",
                                "data-name": p_name,
                                "data-lot": p_lot,
                                "data-price": p_price
                            })
                            td_qty.append(input_qty)
                            new_tr.append(td_qty)
                            
                            tbody.append(new_tr)

                    # 3. 新規・変更された画像を正方形リサイズしてアップロード
                    for p_name, img_file in st.session_state.image_updates.items():
                        safe_name = re.sub(r'[^\w\-_]', '_', p_name)
                        img_filename = f"{safe_name}.jpg"
                        remote_img_path = f"cyumon/images/{img_filename}"
                        
                        img = Image.open(img_file)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        
                        target_size = (400, 400)
                        img.thumbnail(target_size, Image.Resampling.LANCZOS)
                        
                        new_img = Image.new("RGB", target_size, (255, 255, 255))
                        paste_x = (target_size[0] - img.width) // 2
                        paste_y = (target_size[1] - img.height) // 2
                        new_img.paste(img, (paste_x, paste_y))
                        
                        temp_img_path = f"temp_{img_filename}"
                        new_img.save(temp_img_path, "JPEG", quality=90)
                        
                        with open(temp_img_path, "rb") as f:
                            ftp.storbinary(f"STOR {remote_img_path}", f)
                        
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)

                    # ローカル保存してアップロード
                    with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                    
                    with open(LOCAL_HTML_PATH, "rb") as f:
                        ftp.storbinary(f"STOR {REMOTE_HTML_PATH}", f)
                    
                    ftp.quit()
                    st.success("🎉 画像クリックで別タブ拡大表示の機能付きで、サーバーが正常に更新されました！")
                    
                except Exception as e:
                    st.error(f"❌ 更新中にエラーが発生しました: {e}")