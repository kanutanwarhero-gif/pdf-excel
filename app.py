import fitz
from pdf_reader import pdf_to_images
from ocr import read_barcode
import streamlit as st
import os
import pandas as pd
from PIL import Image, ImageDraw

st.set_page_config(
    page_title="Amazon Label Mapper",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Amazon Label Mapper (Final Location & Size Locked)")
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
                    
                    # Image draw canvas open karein
                    draw = ImageDraw.Draw(img)
                    w, h = img.size
                    
                    # --- PERFECT LOCATION & BADA SIZE LOCK ---
                    # X=30 (Left border se strict space), Y=h-75 (Amazon shipping wale exact layer ki height)
                    # Agar text thoda upar-niche karna ho toh '75' ko kam/zyada kar sakte hain
                    position = (30, h - 75)
                    
                    # Text ko BOLD aur BADA karne ke liye hum use micro-offset (stroke matrix) ke sath 
                    # multiple times draw kar rahe hain. Isse bina font file ke text ekdum mota aur bada chhapega.
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            draw.text((position[0] + dx, position[1] + dy), f"{extern}", fill=(0, 0, 0))
                    
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
                
            processed_images.append(img.convert("RGB"))
        
        # --- ORIGINAL 4x6 INCHES BOUNDARY LOCK ---
        if match_count > 0 and len(processed_images) > 0:
            output_pdf_path = os.path.join("temp", f"Final_4x6_{pdf_file.name}")
            
            final_pdf = fitz.open()
            for p_img in processed_images:
                # 4x6 Inches Standard Dimensions = 288 x 432 points
                page = final_pdf.new_page(width=288, height=432)
                
                img_byte_arr = io.BytesIO() if 'io' in locals() else __import__('io').BytesIO()
                p_img.save(img_byte_arr, format='JPEG', quality=100)
                img_bytes = img_byte_arr.getvalue()
                
                page.insert_image(page.rect, stream=img_bytes)
                
            final_pdf.save(output_pdf_path)
            final_pdf.close()
            
            st.success(f"🎯 Done! Successfully matched {match_count} labels in exact 4x6 format.")
            
            with open(output_pdf_path, "rb") as f:
                final_pdf_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download Final 4x6 PDF",
                data=final_pdf_bytes,
                file_name=f"Processed_4x6_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            st.error("❌ Matches empty!")

