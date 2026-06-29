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

st.title("📦 Amazon Label Mapper (Perfect 4x6)")
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
        # CSV clear data alignment
        df.columns = [str(c).strip() for c in df.columns]
        df['Tracking No_str'] = df['Tracking No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # Original PDF ko directly edit karenge taaki orientation aur dimensions (4x6) 100% lock rahein
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
                    
                    page = doc[i]
                    
                    # --- CRITICAL FIX: POSITION AND TEXT FOR 4x6 LAYOUT ---
                    # X=25 (Left shift), Y=page.rect.height - 40 (Bottom alignment dynamically calculated)
                    # Isse orientation hamesha seedhi rahegi
                    y_pos = page.rect.height - 40
                    position = fitz.Point(25, y_pos)
                    
                    # Built-in safe standard font inject ('helv' standard layout engine)
                    # Font size 18 kiya h taaki thermal print me bade aksharon me saaf dikhe
                    page.insert_text(
                        position, 
                        f"{extern}", 
                        fontsize=18, 
                        fontname="helv", 
                        color=(0, 0, 0)
                    )
                    match_count += 1
                else:
                    st.write(f"Page {i+1}: AWB `{awb_clean}` NOT FOUND IN EXCEL")
            else:
                st.write(f"Page {i+1}: BARCODE READ FAILED")
        
        # Final secure saving
        if match_count > 0:
            output_pdf_path = os.path.join("temp", f"Final_Fixed_{pdf_file.name}")
            
            # Save configuration flags updated to freeze changes inside structure permanently
            doc.save(output_pdf_path, garbage=3, deflate=True)
            doc.close()
            
            st.success(f"🎯 Syllabus locked! {match_count} labels processed flawlessly.")
            
            with open(output_pdf_path, "rb") as f:
                final_bytes = f.read()
                
            st.download_button(
                label="📥 Click here to Download Final 4x6 PDF",
                data=final_bytes,
                file_name=f"Processed_4x6_{pdf_file.name}",
                mime="application/pdf"
            )
        else:
            doc.close()
            st.error("❌ Matching process complete, but no records mapped.")

