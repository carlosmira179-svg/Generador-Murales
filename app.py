# ==============================================================================
# GENERADOR AUTOMÁTICO DE MURALES EN PDF - VERSIÓN WEB (STREAMLIT + FPDF2)
# Archivo principal: app.py
# ==============================================================================

import os
import math
import io
import zipfile
import streamlit as st
from PIL import Image
from fpdf import FPDF

A4_WIDTH_CM = 21.0
A4_HEIGHT_CM = 29.7

def cm_to_mm(cm_val):
    return cm_val * 10.0

def procesar_mural_bytes(image_bytes, user_w_cm, target_h_cm, overlap_cm=1.0, auto_prop=True, dpi=300):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    orig_px_w, orig_px_h = img.size
    
    if auto_prop and target_h_cm > 0:
        mural_h_cm = target_h_cm
        mural_w_cm = (orig_px_w * target_h_cm) / orig_px_h
    else:
        mural_w_cm = user_w_cm
        mural_h_cm = target_h_cm

    step_w_cm = A4_WIDTH_CM - overlap_cm
    step_h_cm = A4_HEIGHT_CM - overlap_cm
    
    cols = math.ceil((mural_w_cm - overlap_cm) / step_w_cm)
    rows = math.ceil((mural_h_cm - overlap_cm) / step_h_cm)
    if cols < 1: cols = 1
    if rows < 1: rows = 1
    
    target_pix_w = int((mural_w_cm / 2.54) * dpi)
    target_pix_h = int((mural_h_cm / 2.54) * dpi)
    
    img_resized = img.resize((target_pix_w, target_pix_h), Image.Resampling.LANCZOS)
    
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    
    for r in range(1, rows + 1):
        for col_idx in range(1, cols + 1):
            pdf.add_page()
            
            x_start_cm = (col_idx - 1) * step_w_cm
            y_start_cm = (r - 1) * step_h_cm
            
            x_end_cm = min(x_start_cm + A4_WIDTH_CM, mural_w_cm)
            y_end_cm = min(y_start_cm + A4_HEIGHT_CM, mural_h_cm)
            
            px_left = int((x_start_cm / mural_w_cm) * target_pix_w)
            px_top = int((y_start_cm / mural_h_cm) * target_pix_h)
            px_right = int((x_end_cm / mural_w_cm) * target_pix_w)
            px_bottom = int((y_end_cm / mural_h_cm) * target_pix_h)
            
            tile_crop = img_resized.crop((px_left, px_top, px_right, px_bottom))
            
            # Guardar el recorte en memoria sin tocar disco
            img_buffer = io.BytesIO()
            tile_crop.save(img_buffer, format='JPEG', quality=95)
            img_buffer.seek(0)
            
            tile_w_mm = cm_to_mm(x_end_cm - x_start_cm)
            tile_h_mm = cm_to_mm(y_end_cm - y_start_cm)
            
            pdf.image(img_buffer, x=0, y=0, w=tile_w_mm, h=tile_h_mm)
            
            # Solape derecho
            if col_idx < cols:
                overlap_w_mm = cm_to_mm(overlap_cm)
                right_margin_x_mm = cm_to_mm(A4_WIDTH_CM) - overlap_w_mm
                pdf.set_fill_color(255, 255, 255)
                pdf.rect(right_margin_x_mm, 0, overlap_w_mm, cm_to_mm(A4_HEIGHT_CM), style='F')
                
                pdf.set_draw_color(128, 128, 128)
                pdf.set_line_width(0.2)
                pdf.dashed_line(right_margin_x_mm, 0, right_margin_x_mm, cm_to_mm(A4_HEIGHT_CM), dash_length=1, space_length=1)

            # Pestaña inferior
            overlap_h_mm = cm_to_mm(1.2)
            y_tab_start_mm = cm_to_mm(A4_HEIGHT_CM) - overlap_h_mm
            
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(0, y_tab_start_mm, cm_to_mm(A4_WIDTH_CM), overlap_h_mm, style='F')
            
            pdf.set_draw_color(128, 128, 128)
            pdf.set_line_width(0.2)
            pdf.dashed_line(0, y_tab_start_mm, cm_to_mm(A4_WIDTH_CM), y_tab_start_mm, dash_length=1, space_length=1)
            
            pdf.set_text_color(25, 25, 25)
            pdf.set_font("Helvetica", style="B", size=8)
            label = f"Fila {r} - Columna {col_idx}   |   Mural: {mural_w_cm:.1f}x{mural_h_cm:.1f} cm   |   Solape: {overlap_cm} cm"
            pdf.text(cm_to_mm(0.5), cm_to_mm(A4_HEIGHT_CM) - cm_to_mm(0.4), label)
            
    return bytes(pdf.output())

# ==============================================================================
# INTERFAZ WEB (STREAMLIT)
# ==============================================================================
st.set_page_config(page_title="Generador de Murales A4", page_icon="🖼️")

st.title("🖼️ Generador de Murales A4")
st.write("Subí tus imágenes y generá los archivos PDF listos para imprimir con solape y coordenadas.")

st.sidebar.header("Parámetros del Mural")
target_h_cm = st.sidebar.number_input("Alto del Mural (cm):", value=250.0, step=10.0)
overlap_cm = st.sidebar.number_input("Solape (cm):", value=1.0, step=0.1)

uploaded_files = st.file_uploader("Cargá una o varias imágenes (JPG, PNG, WEBP):", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True)

# El botón ahora SIEMPRE se muestra en pantalla
if st.button("🚀 GENERAR MURALES EN PDF", use_container_width=True):
    if not uploaded_files:
        st.warning("⚠️ Por favor, cargá al menos una imagen arriba antes de generar el PDF.")
    else:
        pdf_outputs = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(uploaded_files)
        
        for idx, file in enumerate(uploaded_files, 1):
            status_text.text(f"Procesando imagen {idx} de {total}: {file.name}...")
            img_bytes = file.read()
            pdf_bytes = procesar_mural_bytes(img_bytes, 0, target_h_cm, overlap_cm, auto_prop=True)
            
            filename_pdf = os.path.splitext(file.name)[0] + "_Mural.pdf"
            pdf_outputs.append((filename_pdf, pdf_bytes))
            
            progress_bar.progress(int((idx / total) * 100))
            
        status_text.success("¡Proceso completado con éxito!")
        
        if len(pdf_outputs) == 1:
            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_outputs[0][1],
                file_name=pdf_outputs[0][0],
                mime="application/pdf",
                use_container_width=True
            )
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for name, data in pdf_outputs:
                    zf.writestr(name, data)
            zip_buffer.seek(0)
            
            st.download_button(
                label="📦 Descargar Todos en un paquete (.ZIP)",
                data=zip_buffer,
                file_name="Murales_Procesados.zip",
                mime="application/zip",
                use_container_width=True
            )
