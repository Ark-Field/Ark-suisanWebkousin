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

st.title("📦 WEB商品価格更新・画像更新・管理ツール")
st.write("即座にサーバーに反映します。")

# --- 設定情報 ---
FTP_HOST = "ftp.arkf.jp"
FTP_USER = "info@arkf.jp"
REMOTE_HTML_PATH = "cyumon/index.html"
LOCAL_HTML_PATH = "index.html"
# ----------------

# セッションステートの初期化
if "products" not in st.session_state:
    st.session_state.products = None
if "edit_products" not in st.session_state:
    st.session_state.edit_products = None
if "other_rows" not in st.session_state:
    st.session_state.other_rows = []
if "image_updates" not in st.session_state:
    st.session_state.image_updates = {}
if "ftp_password" not in st.session_state:
    st.session_state.ftp_password = ""

# サイドバー：接続とデータ読み込み
with st.sidebar:
    st.header("🔑 1. 接続 & データ読込")
    ftp_pass = st.text_input("FTPパスワード", type="password", value=st.session_state.ftp_password)
    if ftp_pass:
        st.session_state.ftp_password = ftp_pass
    
    if st.button("📥 サーバーから商品データを取得", type="primary"):
        if not st.session_state.ftp_password:
            st.error("⚠️ パスワードを入力してください。")
        else:
            try:
                with st.spinner("サーバーからHTMLをダウンロード中..."):
                    ftp = FTP(FTP_HOST)
                    ftp.login(FTP_USER, st.session_state.ftp_password)
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)
                    ftp.quit()
                
                # HTMLを解析して商品リストを抽出
                with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                
                products = []
                other_rows = []
                
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
                    
                    # 送料や税別案内などの特殊行（価格がない、または特定の文言）は別管理にする
                    is_info_row = ("商品（税別" in p_name) or ("サイズ" in p_name and "円" in p_name)
                    
                    row_data = {
                        "id": idx,
                        "商品名": p_name,
                        "ロット": p_lot,
                        "価格": p_price,
                        "備考": p_note,
                        "画像状態": "画像あり" if has_img else "No Image",
                        "img_src": img_src,
                        "html_tr": str(tr) # その他の行はHTMLをそのまま保持
                    }
                    
                    if is_info_row:
                        other_rows.append(row_data)
                    else:
                        products.append(row_data)
                
                st.session_state.products = products
                st.session_state.other_rows = other_rows
                
                for i, p in enumerate(products):
                    p["order"] = i + 1
                st.session_state.edit_products = [dict(p) for p in products]
                st.success(f"✅ 商品 {len(products)}件、案内行 {len(other_rows)}件 を正常に読み込みました！")
            except Exception as e:
                st.error(f"❌ エラー: {e}")

# メイン画面：データが読み込まれたら編集UIを表示
if st.session_state.products is None:
    st.info("👈 まず左側のサイドバーにFTPパスワードを入力し、「サーバーから商品データを取得」ボタンを押してください。")
else:
    st.markdown("---")
    st.subheader("📝 2. 商品情報の編集・並び替え・行の追加・削除")
    st.write("各行の「**並び順番号**」に数字（1, 2, 3...）を入力し、下の **[🔄 この番号順に並び替える]** ボタンを押すと、商品のみ綺麗に並び替わります。")
    
    if st.session_state.edit_products is None:
        st.session_state.edit_products = [dict(p) for p in st.session_state.products]

    if st.button("🔄 入力された「並び順番号」の通りに並び替える", type="primary"):
        for i, prod in enumerate(st.session_state.edit_products):
            if f"order_{i}" in st.session_state:
                try:
                    prod["order"] = int(st.session_state[f"order_{i}"])
                except ValueError:
                    prod["order"] = i + 1
            if f"name_{i}" in st.session_state:
                prod["商品名"] = st.session_state[f"name_{i}"]
            if f"lot_{i}" in st.session_state:
                prod["ロット"] = st.session_state[f"lot_{i}"]
            if f"price_{i}" in st.session_state:
                prod["価格"] = st.session_state[f"price_{i}"]
            if f"note_{i}" in st.session_state:
                prod["備考"] = st.session_state[f"note_{i}"]
        
        st.session_state.edit_products = sorted(st.session_state.edit_products, key=lambda x: x.get("order", 999))
        for idx, p in enumerate(st.session_state.edit_products):
            p["order"] = idx + 1
        st.success("✨ 並び順を更新しました！")
        st.rerun()

    st.markdown("---")

    h_cols = st.columns([0.8, 2.5, 1.2, 1.2, 2.5, 0.6])
    h_cols[0].markdown("**並び順**")
    h_cols[1].markdown("**商品名**")
    h_cols[2].markdown("**ロット**")
    h_cols[3].markdown("**価格**")
    h_cols[4].markdown("**備考**")
    h_cols[5].markdown("**削除**")

    updated_products = []
    for i, prod in enumerate(st.session_state.edit_products):
        cols = st.columns([0.8, 2.5, 1.2, 1.2, 2.5, 0.6])
        
        current_order = prod.get("order", i + 1)
        p_order = cols[0].text_input("並び順", value=str(current_order), key=f"order_{i}", label_visibility="collapsed")
        p_name = cols[1].text_input("商品名", value=prod.get("商品名", ""), key=f"name_{i}", label_visibility="collapsed")
        p_lot = cols[2].text_input("ロット", value=prod.get("ロット", ""), key=f"lot_{i}", label_visibility="collapsed")
        p_price = cols[3].text_input("価格", value=prod.get("価格", ""), key=f"price_{i}", label_visibility="collapsed")
        p_note = cols[4].text_input("備考", value=prod.get("備考", ""), key=f"note_{i}", label_visibility="collapsed")
        
        if cols[5].button("🗑️", key=f"del_{i}"):
            st.session_state.edit_products.pop(i)
            st.rerun()
            
        try:
            order_val = int(p_order)
        except ValueError:
            order_val = i + 1

        updated_products.append({
            "id": prod.get("id", i),
            "order": order_val,
            "商品名": p_name,
            "ロット": p_lot,
            "価格": p_price,
            "備考": p_note,
            "画像状態": prod.get("画像状態", "No Image"),
            "img_src": prod.get("img_src", "")
        })

    st.session_state.edit_products = updated_products

    if st.button("➕ 新しい商品行を追加する"):
        st.session_state.edit_products.append({
            "id": len(st.session_state.edit_products),
            "order": len(st.session_state.edit_products) + 1,
            "商品名": "",
            "ロット": "",
            "価格": "",
            "備考": "",
            "画像状態": "No Image",
            "img_src": ""
        })
        st.rerun()

    st.markdown("---")
    st.subheader("🖼️ 3. 写真（画像）の入れ替え・追加（自動正方形リサイズ）")
    product_names = [name for name in [p.get("商品名", "") for p in st.session_state.edit_products] if name.strip() != ""]
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
            if col2.button("解除", key=f"del_img_{p_name}"):
                del st.session_state.image_updates[p_name]
                st.rerun()

    st.markdown("---")
    st.subheader("🚀 4. サーバーへの反映")
    st.info("並び替え・編集・追加・削除が終わったら、下のボタンを押すと一括でサーバーが更新されます。")
    
    if st.button("変更を保存してサーバー（FTP）に反映する", type="primary"):
        if not st.session_state.ftp_password:
            st.error("⚠️ 左側のサイドバーにFTPパスワードを入力してください。")
        else:
            with st.spinner("サーバーのHTMLを更新し、画像をアップロード中..."):
                try:
                    ftp = FTP(FTP_HOST)
                    ftp.login(FTP_USER, st.session_state.ftp_password)
                    
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {REMOTE_HTML_PATH}", f.write)
                    
                    with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")
                    
                    today_str = datetime.now().strftime("価格表更新日：%Y年%m月%d日")
                    date_element = soup.find(class_="update-date")
                    if date_element:
                        date_element.string = today_str
                    
                    tbody = soup.find("tbody")
                    if tbody:
                        tbody.clear()
                        
                        # 1. 通常商品を書き込み
                        for row in st.session_state.edit_products:
                            p_name = str(row.get("商品名", "")).strip()
                            if not p_name:
                                continue
                            
                            p_lot = str(row.get("ロット", "")).strip()
                            p_price = str(row.get("価格", "")).strip()
                            p_note = str(row.get("備考", "")).strip()
                            
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

                            new_tr = soup.new_tag("tr")
                            
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
                            
                            td_name = soup.new_tag("td", attrs={"class": "name-col"})
                            div_pname = soup.new_tag("div", attrs={"class": "product-name"})
                            div_pname.string = p_name
                            td_name.append(div_pname)
                            
                            div_plot = soup.new_tag("div", attrs={"class": "product-lot"})
                            div_plot.string = f"ロット: {p_lot}"
                            td_name.append(div_plot)
                            new_tr.append(td_name)
                            
                            td_price = soup.new_tag("td", attrs={"class": "price-col"})
                            td_price.string = p_price
                            new_tr.append(td_price)
                            
                            td_note = soup.new_tag("td", attrs={"class": "note-col"})
                            td_note.string = p_note
                            new_tr.append(td_note)
                            
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
                        
                        # 2. 保持していた送料・案内行をそのまま末尾に再追加
                        for other in st.session_state.other_rows:
                            other_tr = BeautifulSoup(other["html_tr"], "html.parser").tr
                            if other_tr:
                                tbody.append(other_tr)

                    # 3. 画像アップロード
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

                    with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                    
                    with open(LOCAL_HTML_PATH, "rb") as f:
                        ftp.storbinary(f"STOR {REMOTE_HTML_PATH}", f)
                    
                    ftp.quit()
                    st.success("🎉 商品の並び順と変更内容がサーバーに正常に反映されました！")
                    
                except Exception as e:
                    st.error(f"❌ 更新中にエラーが発生しました: {e}")