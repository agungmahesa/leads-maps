import streamlit as st
import pandas as pd
import time
from google_maps_crawler import crawl_google_maps
import base64
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Google Maps Restaurant Crawler",
    page_icon="📍",
    layout="wide"
)

# Custom CSS for premium look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .stDownloadButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #28a745;
        color: white;
    }
    .st-emotion-cache-16idsys {
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# App Title
st.title("📍 Google Maps Restaurant Crawler")
st.markdown("Cari dan unduh data kuliner dari daerah mana pun dengan mudah.")

# Sidebar for inputs
with st.sidebar:
    st.header("Pencarian")
    
    area = st.text_input("Area / Lokasi", placeholder="Contoh: Dago, Bandung")
    
    category_options = ["Restoran", "Cafe", "Kedai Kopi", "Bakso", "Mie Ayam", "Warung Makan", "Pizza", "Seafood", "Fast Food"]
    selected_categories = st.multiselect("Kategori Tempat (Bisa lebih dari satu)", options=category_options, default=["Restoran"])
    custom_category = st.text_input("Kategori Lainnya (Opsional)", placeholder="Contoh: Sushi, Gelato")
    
    limit = st.number_input("Jumlah Maksimal Hasil", min_value=1, max_value=200, value=20)
    
    st.divider()
    st.markdown("### Konfigurasi Cloud ☁️")
    apify_token = st.text_input("Apify API Token", type="password", help="Dapatkan di console.apify.com/account?tab=integrations")

    st.divider()
    st.markdown("### Options")
    enable_filter = st.checkbox("Aktifkan Filter Usia Ulasan", value=False)
    max_days = 9999
    if enable_filter:
        max_days = st.slider("Maksimal Usia Review Terakhir (Hari)", 0, 365, 365, help="Sembunyikan tempat yang tidak ada ulasan dalam periode tertentu")
    
    fetch_details = st.checkbox("Scraping Deep (Slow)", value=True, help="Otomatis mengekstrak kontak Instagram jika website tersedia")
    
    run_button = st.button("🚀 Start Cloud Crawling")

# Construct query from inputs
cats = list(selected_categories)
if custom_category:
    cats.append(custom_category)

cat_str = " ".join(cats)
if cat_str and area:
    query = f"{cat_str} di {area}"
elif cat_str:
    query = cat_str
else:
    query = area

# Main display area
if run_button:
    if not apify_token:
        st.error("Silakan masukkan Apify API Token Anda terlebih dahulu supaya bot bisa berjalan di awan!")
    elif not query.strip():
        st.error("Silakan masukkan minimal Area atau Kategori terlebih dahulu!")
    else:
        with st.status(f"Cloud Crawling: {query}...", expanded=True) as status:
            st.write("Menghubungkan ke Apify server...")
            try:
                results = crawl_google_maps(
                    api_token=apify_token,
                    search_query=query, 
                    max_results=limit, 
                    fetch_details=fetch_details
                )
                
                if results:
                    df = pd.DataFrame(results)
                    df = df.drop_duplicates(subset=['name', 'address']).reset_index(drop=True)
                    
                    # Filtering based on last review
                    if 'days_ago' in df.columns:
                        original_count = len(df)
                        if enable_filter:
                            df = df[df['days_ago'] <= max_days].reset_index(drop=True)
                            filtered_count = len(df)
                            st.info(f"Filter ON: Menampilkan {filtered_count} dari {original_count} tempat (Review < {max_days} hari).")
                        else:
                            st.info(f"Filter OFF: Menampilkan seluruh {original_count} tempat.")
                    
                    status.update(label=f"Berhasil mengambil {len(df)} data!", state="complete", expanded=False)
                    
                    st.success(f"Ditemukan {len(df)} data untuk '{query}'")
                    
                    # Display data
                    st.dataframe(df, use_container_width=True)
                    
                    # Export buttons
                    col1, col2 = st.columns(2)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    col1.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f'results_{query.replace(" ", "_")}.csv',
                        mime='text/csv',
                    )
                    
                    # Excel export
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    excel_data = output.getvalue()
                    col2.download_button(
                        label="📝 Download Excel",
                        data=excel_data,
                        file_name=f'results_{query.replace(" ", "_")}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
                else:
                    status.update(label="Tidak ada data ditemukan.", state="error")
                    st.warning("Coba gunakan kata kunci yang lebih spesifik.")
            except Exception as e:
                status.update(label=f"Terjadi kesalahan: {e}", state="error")
                st.error(f"Error: {e}")

else:
    # Landing state
    st.info("← Masukkan pengaturan di panel samping dan klik 'Start Crawling' untuk memulai.")
    
    # Feature instructions
    st.markdown("""
    ### Panduan Penggunaan
    1.  **Daerah/Kata Kunci**: Masukkan apa yang ingin Anda cari (misal: 'Cafe di Braga Bandung').
    2.  **Jumlah Maksimal**: Batasi berapa banyak hasil yang ingin diambil.
    3.  **Headless Mode**: Jika dicentang, browser tidak akan muncul di layar (lebih cepat & stabil).
    4.  **Fetch Details**: Aktifkan jika Anda butuh nomor telepon dan link website (proses akan lebih lambat).
    """)
