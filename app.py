import fitz
from pdf_reader import pdf_to_images
from ocr import read_barcode
import streamlit as st
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont  # Image par direct write karne ke liye

st.set_page_config(
    page_title="Amazon Label Mapper",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Amazon Label Mapper")
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
        # CSV clean matching setup
        df.columns = [str(c).strip() for c in df.columns]
        df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # Original code se image frames read karna
        images = pdf_to_images(pdf_path)
        processed_images = []
        match_count = 0
        
        st.info(f"⚡ Total {len(images)} pages process ho rahe hain...")
        
        for i, img in enumerate(images):
            awb = read_barcode(img)
            
            # Agar img direct PIL Image nahi h, toh ensure karein ki conversion sahi ho
            if not isinstance(img, Image.Image):
                # Agar image bytes ya numpy array me h toh handle karne ke liye wrapper
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
                    
                    # --- DIRECT IMAGE STAMP LOGIC ---
                    # Hum direct image array par canvas draw karenge, koi PDF conflict nahi hoga
                    draw = ImageDraw.Draw(img)
                    
                    # Target Location: Amazon Shipping ke bottom row me left side box alignment
                    # Image pixels ke hisab se exact coordinates scale down lock: (X=40, Y=height-60)
                    w, h = img.size
                    position = (40, h - 60)
                    
                    # Image par text write command execution
                    draw.text(position, f"{extern}", fill=(0, 0, 0))
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
                
            # Processed ya unmodified image ko final list me store karein
            processed_images.append(img.convert("RGB"))
        
        # 3. FRESH PDF CONVERSION FROM UPDATED IMAGES
        if match_count > 0 and len(processed_images) > 0:
            output_pdf_path = os.path.join("temp", f"Mapped_{pdf_file.name}")
            
            # Pehli image ko baki images ke sath secure bundle banakar save karein
            processed_images[0].save(
                output_pdf_path, 
                save_all=True, 
                append_images=processed_images[1:]
            )
            
            st.success(f"🎯 Complete! Successfully updated {match_count} pages.")
            
            with open(output_pdf_path, "rb") as f:
                final_pdf_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download Processed PDF",
                data=final_pdf_bytes,
                file_name=f"Processed_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            st.error("❌ Matches empty! Koi bhi page final sheet se match nahi hua.")

