import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import sys

# Konfigurasi halaman
st.set_page_config(
    page_title="ESB vs Scraper Mapping",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fungsi untuk load data dengan error handling
@st.cache_data
def load_data():
    try:
        # Load data ESB
        df_esb = pd.read_csv('Tarikan_data_ESB_3_Pulau_2025.csv')
        
        # Load data scraper
        df_scraper = pd.read_csv('data_3_pulau_final.csv')
        
        # Load hasil matching
        df_matches = pd.read_csv('esb_3pulau_exact_matching_matches.csv')
        
        return df_esb, df_scraper, df_matches
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        st.info("Please make sure all CSV files are in the same directory as this app")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Fungsi untuk membuat peta dengan safety checks
def create_map(df_esb, df_scraper, df_matches):
    try:
        # Collect all coordinates safely
        all_lats = []
        all_lons = []
        
        # ESB coordinates
        if not df_esb.empty and 'latitude' in df_esb.columns and 'longitude' in df_esb.columns:
            esb_lats = df_esb['latitude'].dropna()
            esb_lons = df_esb['longitude'].dropna()
            if len(esb_lats) > 0:
                all_lats.extend(esb_lats)
                all_lons.extend(esb_lons)
        
        # Scraper coordinates
        if not df_scraper.empty and 'latitude' in df_scraper.columns and 'longitude' in df_scraper.columns:
            scraper_lats = df_scraper['latitude'].dropna()
            scraper_lons = df_scraper['longitude'].dropna()
            if len(scraper_lats) > 0:
                all_lats.extend(scraper_lats)
                all_lons.extend(scraper_lons)
        
        # Match coordinates
        if not df_matches.empty:
            if 'latitude_esb' in df_matches.columns and 'longitude_esb' in df_matches.columns:
                match_esb_lats = df_matches['latitude_esb'].dropna()
                match_esb_lons = df_matches['longitude_esb'].dropna()
                if len(match_esb_lats) > 0:
                    all_lats.extend(match_esb_lats)
                    all_lons.extend(match_esb_lons)
        
        # Calculate center or use default
        if len(all_lats) > 0 and len(all_lons) > 0:
            center_lat = np.mean(all_lats)
            center_lon = np.mean(all_lons)
        else:
            center_lat = -6.2  # Default: Jakarta
            center_lon = 106.8
        
        # Buat peta base
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='OpenStreetMap'
        )
        
        # Tambahkan layer groups
        esb_group = folium.FeatureGroup(name='📗 ESB Data (Orange)', show=True)
        scraper_group = folium.FeatureGroup(name='📘 Scraper Data (Blue)', show=True)
        matches_group = folium.FeatureGroup(name='✅ Irisan Match (Green)', show=True)
        
        # 1. Plot data ESB (orange) - dengan safety check
        if not df_esb.empty and 'latitude' in df_esb.columns and 'longitude' in df_esb.columns:
            for idx, row in df_esb.dropna(subset=['latitude', 'longitude']).iterrows():
                try:
                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=4,
                        popup=f"""
                            <b>ESB Data</b><br>
                            Brand: {row.get('brandName', 'N/A')}<br>
                            Alamat: {row.get('address', 'N/A')}<br>
                            Lat: {row['latitude']:.4f}, Lon: {row['longitude']:.4f}
                        """,
                        tooltip=f"ESB: {row.get('brandName', 'N/A')}",
                        color='orange',
                        fillColor='orange',
                        fillOpacity=0.7,
                        weight=1
                    ).add_to(esb_group)
                except Exception as e:
                    continue  # Skip invalid coordinates
        
        # 2. Plot data Scraper (biru) - dengan safety check
        if not df_scraper.empty and 'latitude' in df_scraper.columns and 'longitude' in df_scraper.columns:
            for idx, row in df_scraper.dropna(subset=['latitude', 'longitude']).iterrows():
                try:
                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=4,
                        popup=f"""
                            <b>Scraper Data</b><br>
                            Brand: {row.get('brandName', 'N/A')}<br>
                            Alamat: {row.get('address', 'N/A')}<br>
                            Lat: {row['latitude']:.4f}, Lon: {row['longitude']:.4f}
                        """,
                        tooltip=f"Scraper: {row.get('brandName', 'N/A')}",
                        color='blue',
                        fillColor='blue',
                        fillOpacity=0.7,
                        weight=1
                    ).add_to(scraper_group)
                except Exception as e:
                    continue  # Skip invalid coordinates
        
        # 3. Plot irisan/match (hijau) - dengan safety check
        if not df_matches.empty:
            for idx, row in df_matches.iterrows():
                try:
                    # Pastikan koordinat valid
                    if (pd.notna(row['latitude_esb']) and pd.notna(row['longitude_esb']) and 
                        pd.notna(row['latitude_pulau']) and pd.notna(row['longitude_pulau'])):
                        
                        # Buat polyline antara ESB dan Scraper untuk match
                        folium.PolyLine(
                            locations=[
                                [row['latitude_esb'], row['longitude_esb']],
                                [row['latitude_pulau'], row['longitude_pulau']]
                            ],
                            color='green',
                            weight=2,
                            opacity=0.6,
                            popup=f"""
                                <b>Match Result</b><br>
                                Confidence: {row.get('match_confidence', 0):.3f}<br>
                                Distance: {row.get('distance_m', 0):.1f}m<br>
                                ESB: {row.get('brandName_esb', 'N/A')}<br>
                                Scraper: {row.get('brandName_pulau', 'N/A')}
                            """
                        ).add_to(matches_group)
                        
                        # Titik ESB dari match (hijau)
                        folium.CircleMarker(
                            location=[row['latitude_esb'], row['longitude_esb']],
                            radius=6,
                            popup=f"""
                                <b>ESB (Match)</b><br>
                                Brand: {row.get('brandName_esb', 'N/A')}<br>
                                Branch: {row.get('branchName_esb', 'N/A')}<br>
                                Confidence: {row.get('match_confidence', 0):.3f}<br>
                                Match Level: {row.get('match_level', 'N/A')}
                            """,
                            tooltip=f"Match ESB: {row.get('brandName_esb', 'N/A')}",
                            color='green',
                            fillColor='green',
                            fillOpacity=0.9,
                            weight=2
                        ).add_to(matches_group)
                        
                        # Titik Scraper dari match (hijau)
                        folium.CircleMarker(
                            location=[row['latitude_pulau'], row['longitude_pulau']],
                            radius=6,
                            popup=f"""
                                <b>Scraper (Match)</b><br>
                                Brand: {row.get('brandName_pulau', 'N/A')}<br>
                                Distance: {row.get('distance_m', 0):.1f}m<br>
                                Address Words: {row.get('address_common_words', 0)}
                            """,
                            tooltip=f"Match Scraper: {row.get('brandName_pulau', 'N/A')}",
                            color='darkgreen',
                            fillColor='darkgreen',
                            fillOpacity=0.9,
                            weight=2
                        ).add_to(matches_group)
                except Exception as e:
                    continue  # Skip invalid match rows
        
        # Tambahkan semua groups ke peta
        esb_group.add_to(m)
        scraper_group.add_to(m)
        matches_group.add_to(m)
        
        # Tambahkan layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    except Exception as e:
        st.error(f"Error creating map: {e}")
        # Return default map as fallback
        return folium.Map(location=[-6.2, 106.8], zoom_start=10)

# Main app
def main():
    st.title("📍 ESB vs Scraper Data Mapping")
    st.markdown("Visualisasi hasil matching data ESB dengan data Scraper 3 Pulau")
    
    # Sidebar
    st.sidebar.header("Dashboard Controls")
    
    # Load data
    with st.spinner('Loading data...'):
        df_esb, df_scraper, df_matches = load_data()
    
    # Check if data loaded successfully
    if df_esb.empty or df_scraper.empty or df_matches.empty:
        st.error("❌ Failed to load one or more data files. Please check:")
        st.info("""
        1. All CSV files are in the same directory
        2. File names are correct:
           - Tarikan_data_ESB_3_Pulau_2025.csv
           - data_3_pulau_final.csv  
           - esb_3pulau_exact_matching_matches.csv
        3. Files are properly committed to GitHub
        """)
        return
    
    # Tampilkan statistics di sidebar
    st.sidebar.subheader("📊 Statistics")
    st.sidebar.metric("Total ESB Data", f"{len(df_esb):,}")
    st.sidebar.metric("Total Scraper Data", f"{len(df_scraper):,}")
    st.sidebar.metric("Successful Matches", f"{len(df_matches):,}")
    
    match_rate = (len(df_matches) / len(df_esb)) * 100 if len(df_esb) > 0 else 0
    st.sidebar.metric("Match Rate", f"{match_rate:.2f}%")
    
    # Filter options
    st.sidebar.subheader("🔍 Filter Options")
    
    # Confidence filter
    min_confidence = st.sidebar.slider(
        "Minimum Confidence Score",
        min_value=0.0,
        max_value=1.0,
        value=0.6,
        step=0.05,
        help="Filter matches based on confidence score"
    )
    
    # Distance filter
    max_distance = st.sidebar.slider(
        "Maximum Distance (meters)",
        min_value=0,
        max_value=5000,
        value=1000,
        step=100,
        help="Filter matches based on distance between points"
    )
    
    # Apply filters
    try:
        filtered_matches = df_matches[
            (df_matches['match_confidence'] >= min_confidence) & 
            (df_matches['distance_m'] <= max_distance)
        ]
        st.sidebar.metric("Filtered Matches", f"{len(filtered_matches):,}")
    except Exception as e:
        st.error(f"Error applying filters: {e}")
        filtered_matches = df_matches
    
    # Tabs untuk different views
    tab1, tab2, tab3 = st.tabs(["🗺️ Interactive Map", "📈 Match Analysis", "📋 Data Details"])
    
    with tab1:
        st.subheader("Interactive Mapping")
        st.markdown(f"""
        **Legend:**
        - 🟢 **Green**: Successful matches ({len(filtered_matches):,} points)
        - 🟠 **Orange**: ESB data only ({len(df_esb):,} points)  
        - 🔵 **Blue**: Scraper data only ({len(df_scraper):,} points)
        """)
        
        # Buat peta dengan data yang sudah difilter
        map_obj = create_map(df_esb, df_scraper, filtered_matches)
        
        # Tampilkan peta
        st_folium(map_obj, width=1200, height=600)
    
    with tab2:
        st.subheader("Match Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exact_matches = filtered_matches['exact_brand_match'].sum() if 'exact_brand_match' in filtered_matches.columns else 0
            st.metric("Exact Brand Matches", f"{exact_matches:,}")
        
        with col2:
            avg_distance = filtered_matches['distance_m'].mean() if 'distance_m' in filtered_matches.columns else 0
            st.metric("Average Distance", f"{avg_distance:.1f}m")
        
        with col3:
            avg_confidence = filtered_matches['match_confidence'].mean() if 'match_confidence' in filtered_matches.columns else 0
            st.metric("Average Confidence", f"{avg_confidence:.3f}")
        
        # Analysis charts dengan safety checks
        if not filtered_matches.empty:
            if 'match_confidence' in filtered_matches.columns:
                st.subheader("Confidence Score Distribution")
                try:
                    confidence_bins = pd.cut(filtered_matches['match_confidence'], 
                                           bins=[0.6, 0.7, 0.8, 0.9, 1.0], 
                                           right=True)
                    conf_counts = confidence_bins.value_counts().sort_index()
                    st.bar_chart(conf_counts)
                except Exception as e:
                    st.warning("Could not display confidence distribution")
            
            if 'distance_m' in filtered_matches.columns:
                st.subheader("Distance Distribution")
                try:
                    distance_bins = pd.cut(filtered_matches['distance_m'], 
                                         bins=[0, 100, 500, 1000, 5000], 
                                         right=True)
                    dist_counts = distance_bins.value_counts().sort_index()
                    st.bar_chart(dist_counts)
                except Exception as e:
                    st.warning("Could not display distance distribution")
    
    with tab3:
        st.subheader("Match Details")
        
        # Tampilkan tabel dengan matches
        if not filtered_matches.empty:
            display_columns = ['brandName_esb', 'brandName_pulau', 'match_confidence', 'distance_m']
            available_columns = [col for col in display_columns if col in filtered_matches.columns]
            
            if available_columns:
                st.dataframe(
                    filtered_matches[available_columns].sort_values('match_confidence', ascending=False),
                    use_container_width=True
                )
                
                # Download button untuk filtered matches
                try:
                    csv = filtered_matches.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered Matches as CSV",
                        data=csv,
                        file_name=f"filtered_matches_confidence_{min_confidence}_distance_{max_distance}.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.warning("Could not generate download file")
            else:
                st.warning("No match data available to display")
        else:
            st.warning("No matches found with current filters")

if __name__ == "__main__":
    main()
