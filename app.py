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
# FUNGSI: LOAD DATA (OPTIMASI MEMORI)
# ========================================
@st.cache_data
def load_data(max_points=1000):
    try:
        # Kolom yang dibutuhkan
        base_cols = ['latitude', 'longitude', 'brandName', 'address']
        dtype_float = {'latitude': 'float32', 'longitude': 'float32'}
        dtype_cat = {'brandName': 'category'}

        # Load ESB
        df_esb = pd.read_csv('Tarikan_data_ESB_3_Pulau_2025.csv',
                             usecols=base_cols,
                             dtype={**dtype_float, **dtype_cat})

        # Load Scraper
        df_scraper = pd.read_csv('data_3_pulau_final.csv',
                                 usecols=base_cols,
                                 dtype={**dtype_float, **dtype_cat})

        # Load Match
        match_cols = ['latitude_esb', 'longitude_esb', 'latitude_pulau', 'longitude_pulau',
                      'brandName_esb', 'brandName_pulau', 'match_confidence', 'distance_m']
        df_matches = pd.read_csv('esb_3pulau_exact_matching_matches.csv',
                                 usecols=match_cols,
                                 dtype={'latitude_esb': 'float32', 'longitude_esb': 'float32',
                                        'latitude_pulau': 'float32', 'longitude_pulau': 'float32',
                                        'match_confidence': 'float32', 'distance_m': 'float32'})

        # Batasi jumlah titik (sesuai slider)
        df_esb = df_esb.head(max_points).dropna(subset=['latitude', 'longitude'])
        df_scraper = df_scraper.head(max_points).dropna(subset=['latitude', 'longitude'])
        df_matches = df_matches.head(max_points // 2)

        # Monitor RAM
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024 ** 2)
        st.sidebar.write(f"🧠 **RAM digunakan**: {mem_mb:.1f} MB")

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
        # Hitung pusat peta
        all_lats = pd.concat([df_esb['latitude'], df_scraper['latitude']], ignore_index=True)
        all_lons = pd.concat([df_esb['longitude'], df_scraper['longitude']], ignore_index=True)
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
        for _, row in df_matches.iterrows():
            if pd.notna(row['latitude_esb']) and pd.notna(row['longitude_esb']) and \
               pd.notna(row['latitude_pulau']) and pd.notna(row['longitude_pulau']):

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
        st.error("Gagal memuat data. Periksa file CSV di repo.")
        return

    # Filter match
    filtered_matches = df_matches[
        (df_matches['match_confidence'] >= min_confidence) &
        (df_matches['distance_m'] <= max_distance)
    ]

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
            st.metric("Exact Match", filtered_matches.get('exact_brand_match', pd.Series([0])).sum())
        with col2:
            st.metric("Rata-rata Jarak", f"{filtered_matches['distance_m'].mean():.1f} m")
        with col3:
            st.metric("Rata-rata Confidence", f"{filtered_matches['match_confidence'].mean():.3f}")

    with tab3:
        st.subheader("Detail Match")
        if not filtered_matches.empty:
            display_cols = ['brandName_esb', 'brandName_pulau', 'match_confidence', 'distance_m']
            avail_cols = [c for c in display_cols if c in filtered_matches.columns]
            st.dataframe(filtered_matches[avail_cols].sort_values('match_confidence', ascending=False))
        else:
            st.info("Tidak ada match dengan filter saat ini.")

    st.success("✅ App berjalan lancar!")

if __name__ == "__main__":
    main()
