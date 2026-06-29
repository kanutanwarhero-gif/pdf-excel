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

st.title("📦 Amazon Label Mapper (4x6 Size Locked)")
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
        # CSV formatting clean up
        df.columns = [str(c).strip() for c in df.columns]
        df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # --- 4x6 SIZE & LAYOUT LOCK ---
        # Hum direct original PDF frame me hi text injection karenge bina image conversion crash ke
        # Isse page dimensions (4x6 thermal format) 100% same rahega aur stretch nahi hoga
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
                    
                    # Target exact page layer
                    page = doc[i]
                    
                    # --- BADA FONT AUR POSITION SETTING ---
                    # 4x6 page par "amazon shipping" ke left box ke coordinates:
                    # X=20 (Left alignment), Y=540 (Bottom alignment as per 4x6 grid ratio)
                    position = fitz.Point(20, 540)
                    
                    # fontname='helv' (Helvetica) and fontsize=16 with standard black fill
                    # Agar aapko aur bada chahiye toh size 16 ko 18 ya 20 kar sakte hain
                    page.insert_text(
                        position, 
                        f"{extern}", 
                        fontsize=16, 
                        fontname="helv", 
                        color=(0, 0, 0)
                    )
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
        
        # Save output by locking original layout matrix
        if match_count > 0:
            output_pdf_path = os.path.join("temp", f"Processed_4x6_{pdf_file.name}")
            doc.save(output_pdf_path)
            doc.close()
            
            st.success(f"🎯 Complete! {match_count} labels processed in original 4x6 size.")
            
            with open(output_pdf_path, "rb") as f:
                final_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download 4x6 Processed PDF",
                data=final_bytes,
                file_name=f"Processed_4x6_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            doc.close()
            st.error("❌ No matches found.")

