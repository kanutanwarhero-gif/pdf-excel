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
        # 1. Clean headers and formats
        df.columns = [str(c).strip() for c in df.columns]
        df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # 2. Main PDF wrapper setup
        doc = fitz.open(pdf_path)
        images = pdf_to_images(pdf_path)
        match_count = 0
        
        st.info(f"⚡ Processing {len(images)} pages...")
        
        for i, img in enumerate(images):
            awb = read_barcode(img)
            
            if awb:
                awb_clean = str(awb).strip()
                match = df[df["Tracking No_str"] == awb_clean]
                
                if match.empty:
                    match = df[df["Tracking No_str"].str.contains(awb_clean, na=False)]
                
                if not match.empty:
                    extern = str(match.iloc[0]["Extern Order No"])
                    st.write(f"Page {i+1}: Matched -> {extern}")
                    
                    # Target correct PDF frame page layer
                    page = doc[i]
                    
                    # --- POSITION: LEFT SIDE OF AMAZON SHIPPING (BOTTOM) ---
                    # X=20 (Left alignment border frame), Y=955 (Amazon shipping row height)
                    position = fitz.Point(20, 955)
                    
                    # Direct Standard Font (no custom crash assets)
                    page.insert_text(
                        position, 
                        f"{extern}", 
                        fontsize=12, 
                        fontname="helv",
                        color=(0, 0, 0)
                    )
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
        
        # 3. CRITICAL SAVING STEP FOR DOWNLOAD BUFFER
        if match_count > 0:
            # Back-end storage clean write update execution
            output_pdf_path = os.path.join("temp", f"Processed_{pdf_file.name}")
            doc.save(output_pdf_path)
            doc.close()
            
            st.success(f"🎯 Complete! Total {match_count} labels updated successfully.")
            
            # Read back updated file to stream over memory download button
            with open(output_pdf_path, "rb") as f:
                processed_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download Processed PDF",
                data=processed_bytes,
                file_name=f"Processed_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            doc.close()
            st.error("❌ Matches completely empty. Data match fail.")

