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
                    
                    # リモートパスからフォルダ名とファイル名を分解して安全に移動
                    remote_dir = os.path.dirname(REMOTE_HTML_PATH)   # 例: "cyumon"
                    remote_file = os.path.basename(REMOTE_HTML_PATH) # 例: "index.html"
                    
                    if remote_dir:
                        ftp.cwd(remote_dir)
                        
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {remote_file}", f.write)
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
                    
                    is_info_row = ("商品（税別" in p_name) or ("サイズ" in p_name and "円" in p_name)
                    
                    row_data = {
                        "並び順": idx + 1,
                        "商品名": p_name,
                        "ロット": p_lot,
                        "価格": p_price,
                        "備考": p_note,
                        "画像状態": "画像あり" if has_img else "No Image",
                        "img_src": img_src,
                        "html_tr": str(tr)
                    }
                    
                    if is_info_row:
                        other_rows.append(row_data)
                    else:
                        products.append(row_data)
                
                for i, p in enumerate(products):
                    p["並び順"] = i + 1

                st.session_state.products = products
                st.session_state.other_rows = other_rows
                st.success(f"✅ 商品 {len(products)}件、案内行 {len(other_rows)}件 を正常に読み込みました！")
            except Exception as e:
                st.error(f"❌ エラー: {e}")

# メイン画面：データが読み込まれたら編集UIを表示
if st.session_state.products is None:
    st.info("👈 まず左側のサイドバーにFTPパスワードを入力し、「サーバーから商品データを取得」ボタンを押してください。")
else:
    st.markdown("---")
    st.subheader("📝 2. 商品情報の編集・並び替え（番号指定）・行の追加・削除")
    st.write("表の「**並び順**」列に数字（1, 2, 3...）を入力して並び替えるか、下部の **[+]** から新しい行を追加できます。")
    
    df_products = pd.DataFrame(st.session_state.products)
    
    edited_df = st.data_editor(
        df_products[["並び順", "商品名", "ロット", "価格", "備考", "画像状態"]],
        column_config={
            "並び順": st.column_config.NumberColumn("並び順", min_value=1, step=1, width="small"),
            "画像状態": st.column_config.TextColumn("画像状態", disabled=True, width="small"),
            "商品名": st.column_config.TextColumn("商品名", width="medium"),
            "ロット": st.column_config.TextColumn("ロット", width="small"),
            "価格": st.column_config.TextColumn("価格", width="small"),
            "備考": st.column_config.TextColumn("備考", width="small"),
        },
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        key="product_table_editor"
    )

    st.markdown("---")
    st.subheader("🖼️ 3. 写真（画像）の入れ替え・追加（自動正方形リサイズ）")
    
    valid_product_names = [name for name in edited_df["商品名"].dropna().tolist() if str(name).strip() != ""]
    if valid_product_names:
        selected_product = st.selectbox("写真を変更・追加する商品を選択", valid_product_names)
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
    st.info("「並び順」の数字順に自動で並び替えてサーバーに反映されます。")
    
    if st.button("変更を保存してサーバー（FTP）に反映する", type="primary"):
        if not st.session_state.ftp_password:
            st.error("⚠️ 左側のサイドバーにFTPパスワードを入力してください。")
        else:
            with st.spinner("サーバーのHTMLを更新し、画像をアップロード中..."):
                try:
                    sorted_df = edited_df.sort_values(by="並び順", ascending=True).reset_index(drop=True)

                    ftp = FTP(FTP_HOST)
                    ftp.login(FTP_USER, st.session_state.ftp_password)
                    
                    remote_dir = os.path.dirname(REMOTE_HTML_PATH)
                    remote_file = os.path.basename(REMOTE_HTML_PATH)
                    
                    if remote_dir:
                        ftp.cwd(remote_dir)
                    
                    with open(LOCAL_HTML_PATH, "wb") as f:
                        ftp.retrbinary(f"RETR {remote_file}", f.write)
                    
                    with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")
                    
                    today_str = datetime.now().strftime("価格表更新日：%Y年%m月%d日")
                    date_element = soup.find(class_="update-date")
                    if date_element:
                        date_element.string = today_str
                    
                    tbody = soup.find("tbody")
                    if tbody:
                        tbody.clear()
                        
                        for _, row in sorted_df.iterrows():
                            p_name = str(row.get("商品名", "")).strip()
                            if not p_name or p_name == "nan":
                                continue
                            
                            p_lot = str(row.get("ロット", "")).strip()
                            if p_lot == "nan": p_lot = ""
                            
                            p_price = str(row.get("価格", "")).strip()
                            if p_price == "nan": p_price = ""
                            
                            p_note = str(row.get("備考", "")).strip()
                            if p_note == "nan": p_note = ""
                            
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
                            div_plot.string = f"ロット: {p_lot}" if p_lot else "ロット: "
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
                        
                        for other in st.session_state.other_rows:
                            other_tr = BeautifulSoup(other["html_tr"], "html.parser").tr
                            if other_tr:
                                tbody.append(other_tr)

                    # 画像アップロード処理（imagesフォルダに移動してアップロード）
                    try:
                        ftp.cwd("images")
                    except Exception:
                        try:
                            ftp.mkd("images")
                            ftp.cwd("images")
                        except Exception:
                            pass

                    for p_name, img_file in st.session_state.image_updates.items():
                        safe_name = re.sub(r'[^\w\-_]', '_', p_name)
                        img_filename = f"{safe_name}.jpg"
                        
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
                            ftp.storbinary(f"STOR {img_filename}", f)
                        
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)

                    # 元のディレクトリ（cyumon）に戻る
                    ftp.cwd("..")

                    # HTMLの保存とアップロード
                    with open(LOCAL_HTML_PATH, "w", encoding="utf-8") as f:
                        f.write(str(soup))
                    
                    with open(LOCAL_HTML_PATH, "rb") as f:
                        ftp.storbinary(f"STOR {remote_file}", f)
                    
                    ftp.quit()
                    st.success("🎉 指定した「並び順」の通りに並び替えられ、サーバーの更新が完了しました！")
                    
                except Exception as e:
                    st.error(f"❌ 更新中にエラーが発生しました: {e}")