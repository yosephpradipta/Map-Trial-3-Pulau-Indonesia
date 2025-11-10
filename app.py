import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import psutil
from folium.plugins import MarkerCluster

# ========================================
# KONFIGURASI HALAMAN
# ========================================
st.set_page_config(
    page_title="ESB vs Scraper Mapping",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# FUNGSI: LOAD DATA (OPTIMASI MEMORI + AUTO-DETECT KOLOM)
# ========================================
@st.cache_data
def load_data(max_points=1000):
    try:
        # Kolom yang diharapkan (bisa disesuaikan jika perlu)
        base_cols = ['latitude', 'longitude', 'brandName', 'address']  # Ubah jika nama beda, misal 'brand_name'
        match_cols = ['latitude_esb', 'longitude_esb', 'latitude_pulau', 'longitude_pulau',
                      'brandName_esb', 'brandName_pulau', 'match_confidence', 'distance_m']

        # Fungsi helper: Baca header dan filter kolom yang ada
        def safe_read_csv(file_path, expected_cols, dtype_dict=None):
            # Baca header dulu
            header_df = pd.read_csv(file_path, nrows=0)
            available_cols = header_df.columns.tolist()
            
            # Filter kolom yang benar-benar ada
            actual_cols = [col for col in expected_cols if col in available_cols]
            if not actual_cols:
                st.warning(f"Tidak ada kolom yang cocok di {file_path}. Kolom tersedia: {available_cols}")
                return pd.DataFrame()
            
            # Baca data dengan kolom yang ada
            df = pd.read_csv(file_path, usecols=actual_cols, dtype=dtype_dict)
            
            # Debug: Tampilkan di sidebar
            st.sidebar.write(f"📁 **{file_path.split('/')[-1]}**: Kolom dimuat: {actual_cols}")
            
            return df

        # Load ESB
        dtype_base = {'latitude': 'float32', 'longitude': 'float32'}
        df_esb = safe_read_csv('Tarikan_data_ESB_3_Pulau_2025.csv', base_cols, dtype_base)
        
        # Load Scraper
        df_scraper = safe_read_csv('data_3_pulau_final.csv', base_cols, dtype_base)

        # Load Match
        dtype_match = {'latitude_esb': 'float32', 'longitude_esb': 'float32',
                       'latitude_pulau': 'float32', 'longitude_pulau': 'float32',
                       'match_confidence': 'float32', 'distance_m': 'float32'}
        df_matches = safe_read_csv('esb_3pulau_exact_matching_matches.csv', match_cols, dtype_match)

        # Batasi jumlah titik (sesuai slider)
        df_esb = df_esb.head(max_points).dropna(subset=['latitude', 'longitude'])
        df_scraper = df_scraper.head(max_points).dropna(subset=['latitude', 'longitude'])
        df_matches = df_matches.head(max_points // 2)

        # Monitor RAM
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024 ** 2)
        st.sidebar.write(f"🧠 **RAM digunakan**: {mem_mb:.1f} MB")

        # Debug: Tampilkan kolom keseluruhan
        st.sidebar.write("---")
        st.sidebar.write("**Kolom Tersedia di Semua File:**")
        st.sidebar.json({
            'ESB': list(df_esb.columns) if not df_esb.empty else [],
            'Scraper': list(df_scraper.columns) if not df_scraper.empty else [],
            'Matches': list(df_matches.columns) if not df_matches.empty else []
        })

        return df_esb, df_scraper, df_matches

    except FileNotFoundError as e:
        st.error(f"File tidak ditemukan: {e}")
        st.info("Pastikan semua file CSV ada di repo GitHub.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ========================================
# FUNGSI: BUAT PETA DENGAN MARKER CLUSTER
# ========================================
def create_map(df_esb, df_scraper, df_matches):
    try:
        # Hitung pusat peta (skip NaN)
        all_lats = pd.concat([df_esb.get('latitude', pd.Series([])), 
                              df_scraper.get('latitude', pd.Series([]))], ignore_index=True).dropna()
        all_lons = pd.concat([df_esb.get('longitude', pd.Series([])), 
                              df_scraper.get('longitude', pd.Series([]))], ignore_index=True).dropna()
        center_lat = all_lats.mean() if len(all_lats) > 0 else -6.2
        center_lon = all_lons.mean() if len(all_lons) > 0 else 106.8

        # Peta base
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='CartoDB positron',
            prefer_canvas=True
        )

        # Layer groups dengan MarkerCluster
        esb_group = MarkerCluster(name='📗 ESB Data (Orange)').add_to(m)
        scraper_group = MarkerCluster(name='📘 Scraper Data (Blue)').add_to(m)
        match_group = MarkerCluster(name='✅ Match (Green)').add_to(m)

        # === PLOT ESB ===
        if 'latitude' in df_esb.columns and 'longitude' in df_esb.columns:
            for _, row in df_esb.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=4,
                    color='orange',
                    fillColor='orange',
                    fillOpacity=0.7,
                    weight=1,
                    popup=folium.Popup(
                        f"<b>ESB</b><br>"
                        f"Brand: {row.get('brandName', 'N/A')}<br>"
                        f"Alamat: {row.get('address', 'N/A')}",
                        max_width=300
                    ),
                    tooltip=f"ESB: {row.get('brandName', 'N/A')}"
                ).add_to(esb_group)

        # === PLOT SCRAPER ===
        if 'latitude' in df_scraper.columns and 'longitude' in df_scraper.columns:
            for _, row in df_scraper.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=4,
                    color='blue',
                    fillColor='blue',
                    fillOpacity=0.7,
                    weight=1,
                    popup=folium.Popup(
                        f"<b>Scraper</b><br>"
                        f"Brand: {row.get('brandName', 'N/A')}<br>"
                        f"Alamat: {row.get('address', 'N/A')}",
                        max_width=300
                    ),
                    tooltip=f"Scraper: {row.get('brandName', 'N/A')}"
                ).add_to(scraper_group)

        # === PLOT MATCH ===
        if not df_matches.empty and all(col in df_matches.columns for col in ['latitude_esb', 'longitude_esb', 'latitude_pulau', 'longitude_pulau']):
            for _, row in df_matches.iterrows():
                if (pd.notna(row['latitude_esb']) and pd.notna(row['longitude_esb']) and
                    pd.notna(row['latitude_pulau']) and pd.notna(row['longitude_pulau'])):

                    # Garis match
                    folium.PolyLine(
                        locations=[
                            [row['latitude_esb'], row['longitude_esb']],
                            [row['latitude_pulau'], row['longitude_pulau']]
                        ],
                        color='green',
                        weight=2,
                        opacity=0.6,
                        popup=folium.Popup(
                            f"<b>Match</b><br>"
                            f"Confidence: {row.get('match_confidence', 0):.3f}<br>"
                            f"Jarak: {row.get('distance_m', 0):.1f} m<br>"
                            f"ESB: {row.get('brandName_esb', 'N/A')}<br>"
                            f"Scraper: {row.get('brandName_pulau', 'N/A')}",
                            max_width=300
                        )
                    ).add_to(match_group)

                    # Titik ESB
                    folium.CircleMarker(
                        location=[row['latitude_esb'], row['longitude_esb']],
                        radius=6, color='green', fillOpacity=0.9,
                        popup=folium.Popup(f"<b>ESB Match</b><br>{row.get('brandName_esb', 'N/A')}")
                    ).add_to(match_group)

                    # Titik Scraper
                    folium.CircleMarker(
                        location=[row['latitude_pulau'], row['longitude_pulau']],
                        radius=6, color='darkgreen', fillOpacity=0.9,
                        popup=folium.Popup(f"<b>Scraper Match</b><br>{row.get('brandName_pulau', 'N/A')}")
                    ).add_to(match_group)

        # Layer control
        folium.LayerControl().add_to(m)

        return m

    except Exception as e:
        st.error(f"Error membuat peta: {e}")
        return folium.Map(location=[-6.2, 106.8], zoom_start=10)


# ========================================
# MAIN APP
# ========================================
def main():
    st.title("📍 ESB vs Scraper Data Mapping")
    st.markdown("Visualisasi hasil matching data ESB & Scraper 3 Pulau")

    # Sidebar Controls
    st.sidebar.header("⚙️ Kontrol Dashboard")

    max_points = st.sidebar.slider(
        "🔍 Maksimal titik per layer",
        min_value=100,
        max_value=5000,
        value=1000,
        step=500,
        help="Kurangi untuk hemat memori"
    )

    min_confidence = st.sidebar.slider(
        "Minimum Confidence",
        0.0, 1.0, 0.6, 0.05
    )
    max_distance = st.sidebar.slider(
        "Maksimal Jarak (meter)",
        0, 5000, 1000, 100
    )

    # Load data
    with st.spinner('Memuat data...'):
        df_esb, df_scraper, df_matches = load_data(max_points)

    if df_esb.empty or df_scraper.empty:
        st.error("Gagal memuat data utama. Periksa file CSV di repo.")
        st.info("Tips: Cek nama kolom di sidebar untuk debug.")
        return

    # Filter match (hanya jika ada kolomnya)
    if not df_matches.empty and 'match_confidence' in df_matches.columns and 'distance_m' in df_matches.columns:
        filtered_matches = df_matches[
            (df_matches['match_confidence'] >= min_confidence) &
            (df_matches['distance_m'] <= max_distance)
        ]
    else:
        filtered_matches = pd.DataFrame()

    # Stats
    st.sidebar.subheader("📊 Statistik")
    st.sidebar.metric("ESB Data", f"{len(df_esb):,}")
    st.sidebar.metric("Scraper Data", f"{len(df_scraper):,}")
    st.sidebar.metric("Match (setelah filter)", f"{len(filtered_matches):,}")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🗺️ Peta Interaktif", "📈 Analisis", "📋 Detail"])

    with tab1:
        st.subheader("Peta Interaktif")
        map_obj = create_map(df_esb, df_scraper, filtered_matches)
        st_folium(map_obj, width=1200, height=600, key="map")

    with tab2:
        st.subheader("Ringkasan Match")
        col1, col2, col3 = st.columns(3)
        with col1:
            exact_count = filtered_matches.get('exact_brand_match', pd.Series([0])).sum() if not filtered_matches.empty else 0
            st.metric("Exact Match", exact_count)
        with col2:
            avg_dist = filtered_matches['distance_m'].mean() if not filtered_matches.empty and 'distance_m' in filtered_matches.columns else 0
            st.metric("Rata-rata Jarak", f"{avg_dist:.1f} m")
        with col3:
            avg_conf = filtered_matches['match_confidence'].mean() if not filtered_matches.empty and 'match_confidence' in filtered_matches.columns else 0
            st.metric("Rata-rata Confidence", f"{avg_conf:.3f}")

    with tab3:
        st.subheader("Detail Match")
        if not filtered_matches.empty:
            display_cols = ['brandName_esb', 'brandName_pulau', 'match_confidence', 'distance_m']
            avail_cols = [c for c in display_cols if c in filtered_matches.columns]
            if avail_cols:
                st.dataframe(filtered_matches[avail_cols].sort_values('match_confidence', ascending=False))
            else:
                st.info("Kolom match tidak ditemukan.")
        else:
            st.info("Tidak ada match dengan filter saat ini.")

    st.success("✅ App berjalan lancar!")

if __name__ == "__main__":
    main()
