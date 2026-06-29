import fitz
from pdf_reader import pdf_to_images
from ocr import read_barcode
import streamlit as st
import os
import pandas as pd

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
        # 1. Clean CSV Tracking numbers to avoid match failure
        df.columns = [str(c).strip() for c in df.columns]
        if 'Tracking No' in df.columns and 'Extern Order No' in df.columns:
            df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # 2. PyMuPDF se main document open karein text stamp karne ke liye
            doc = fitz.open(pdf_path)
            
            # Aapka function image convert karega barcode reading ke liye
            images = pdf_to_images(pdf_path)
            match_count = 0
            
            st.info(f"⚡ Total {len(images)} pages process ho rahe hain...")
            
            for i, img in enumerate(images):
                awb = read_barcode(img)
                
                if awb:
                    awb_clean = str(awb).strip()
                    # Clean match verification
                    match = df[df["Tracking No_str"] == awb_clean]
                    
                    if match.empty:
                        match = df[df["Tracking No_str"].str.contains(awb_clean, na=False)]
                    
                    if not match.empty:
                        extern = str(match.iloc[0]["Extern Order No"])
                        st.write(f"Page {i+1}: Matched -> {extern}")
                        
                        # Target specific page
                        page = doc[i]
                        
                        # --- BOTTOM LEFT OF AMAZON SHIPPING ---
                        # Amazon Shipping label ke bottom left me blank box ke paas coordinates:
                        # X = 20 (Left aligned), Y = 955 (Bottom bar alignment)
                        position = fitz.Point(20, 955)
                        
                        # Bina kisi external font file dependency ke clean extraction text insert:
                        page.insert_text(
                            position, 
                            f"EXT: {extern}", 
                            fontsize=14, 
                            color=(0, 0, 0)
                        )
                        match_count += 1
                    else:
                        st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
                else:
                    st.write(f"Page {i+1}: BARCODE READ FAILED")
            
            # 3. Processed file ko download ke liye save karein
            if match_count > 0:
                st.success(f"🎯 Complete! Successfully updated {match_count} pages.")
                output_pdf_bytes = doc.write()
                st.download_button(
                    label="📥 Processed PDF Download Karein",
                    data=output_pdf_bytes,
                    file_name="Mapped_Amazon_Labels.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("❌ Kisi bhi label ka barcode excel data se match nahi hua.")
        else:
            st.error("❌ Excel sheet headers verify karein ('Tracking No' aur 'Extern Order No' hona chahiye).")

