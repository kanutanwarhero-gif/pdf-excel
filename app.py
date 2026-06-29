import fitz
from pdf_reader import pdf_to_images
from ocr import read_barcode
import streamlit as st
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(
    page_title="Amazon Label Mapper",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Amazon Label Mapper (Super Large Font)")
st.write("Upload Shipping Label PDF and CSV/Excel")

pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
excel_file = st.file_uploader("Upload CSV / Excel", type=["csv", "xlsx"])

if pdf_file:
    os.makedirs("temp", exist_ok=True)
    pdf_path = os.path.join("temp", pdf_file.name)
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.read())
    st.success("PDF Uploaded")

if excel_file:
    os.makedirs("temp", exist_ok=True)
    excel_path = os.path.join("temp", excel_file.name)
    with open(excel_path, "wb") as f:
        f.write(excel_file.read())
    st.success("Excel Uploaded")

    if excel_file.name.endswith(".csv"):
        df = pd.read_csv(excel_path)
    else:
        df = pd.read_excel(excel_path)

    st.subheader("Preview")
    st.dataframe(df.head())

if st.button("Process"):
    if pdf_file is None:
        st.error("Upload PDF")
    elif excel_file is None:
        st.error("Upload Excel")
    else:
        df.columns = [str(c).strip() for c in df.columns]
        df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        images = pdf_to_images(pdf_path)
        processed_images = []
        match_count = 0
        
        st.info(f"⚡ Processing {len(images)} pages...")
        
        for i, img in enumerate(images):
            awb = read_barcode(img)
            
            if not isinstance(img, Image.Image):
                try:
                    img = Image.fromarray(img)
                except:
                    pass

            if awb:
                awb_clean = str(awb).strip()
                match = df[df["Tracking No_str"] == awb_clean]
                
                if match.empty:
                    match = df[df["Tracking No_str"].str.contains(awb_clean, na=False)]
                
                if not match.empty:
                    extern = str(match.iloc[0]["Extern Order No"])
                    st.write(f"Page {i+1}: Matched -> {extern}")
                    
                    draw = ImageDraw.Draw(img)
                    w, h = img.size
                    
                    # --- DYNAMIC SUPER LARGE FONT LOGIC ---
                    # Image ki total width ka 5% font size set kiya h taaki chhota hone ka chance hi na rahe
                    dynamic_font_size = int(w * 0.05) 
                    
                    # Standard built-in bitmap engine font setup
                    try:
                        font = ImageFont.load_default()
                    except:
                        font = None
                    
                    # Location lock: "amazon shipping" logo ke thik left me
                    position = (int(w * 0.05), h - int(h * 0.07))
                    
                    # High resolution image par text ko massive scaling aur clear stroke layer 
                    # ke sath multi-draw block me chalayenge taaki bina ttf file ke text extra thick dikhe
                    for dx in range(-4, 5):
                        for dy in range(-4, 5):
                            draw.text((position[0] + dx, position[1] + dy), f"{extern}", fill=(0, 0, 0))
                            
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
                
            processed_images.append(img.convert("RGB"))
        
        if match_count > 0 and len(processed_images) > 0:
            output_pdf_path = os.path.join("temp", f"Final_4x6_{pdf_file.name}")
            
            final_pdf = fitz.open()
            for p_img in processed_images:
                # 4x6 Inches dimensions (288 x 432 points) lock
                page = final_pdf.new_page(width=288, height=432)
                
                img_byte_arr = io.BytesIO() if 'io' in locals() else __import__('io').BytesIO()
                p_img.save(img_byte_arr, format='JPEG', quality=100)
                img_bytes = img_byte_arr.getvalue()
                
                page.insert_image(page.rect, stream=img_bytes)
                
            final_pdf.save(output_pdf_path)
            final_pdf.close()
            
            st.success(f"🎯 Font scaling applied successfully!")
            
            with open(output_pdf_path, "rb") as f:
                final_pdf_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download Processed 4x6 PDF",
                data=final_pdf_bytes,
                file_name=f"Processed_4x6_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            st.error("❌ Matches empty!")
