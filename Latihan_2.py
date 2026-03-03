import streamlit as st
import pandas as pd
import numpy as np
import json
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from pyproj import Transformer 

# --- KONFIGURASI KATA LALUAN & ID (TAMBAHAN) ---
KATA_LALUAN_BETUL = "admin1060"
SENARAI_USER = {
    "1": "OOI SUE ANN",
    "2": "WONG YUEAN YI",
    "3": "CHAN BOON YEAH"
}

# --- FUNGSI UTAMA ---
def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    
    # Sudut untuk putaran teks (Matplotlib & CSS)
    text_angle = np.degrees(np.arctan2(dn, de))
    
    # Pelarasan sudut untuk teks supaya tidak terbalik
    if text_angle > 90:
        text_angle -= 180
    elif text_angle < -90:
        text_angle += 180
        
    return to_dms(bearing), jarak, text_angle

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- FUNGSI PENUKARAN KOORDINAT TEPAT (UTM ke WGS84) ---
def grid_to_latlong(easting, northing, epsg_code):
    try:
        # Transformer dari UTM ke WGS84 (EPSG:4326)
        transformer = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(easting, northing)
        return lat, lon
    except:
        return None, None

# --- UI STREAMLIT ---
st.set_page_config(page_title="SISTEM PENGURUSAN MAKLUMAT TANAH", layout="wide")

# --- SISTEM LOGIN (DIKEMASKINI: TAMBAH LOGIK SALAH 3 KALI) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
# Tambahan state untuk menjejak baki percubaan
if "attempts" not in st.session_state:
    st.session_state["attempts"] = 0
if "current_password" not in st.session_state:
    st.session_state["current_password"] = KATA_LALUAN_BETUL
if "show_reset" not in st.session_state:
    st.session_state["show_reset"] = False

if not st.session_state["authenticated"]:
    # LOGO BESAR DI HALAMAN LOGIN
    try:
        st.image("puo-1.png", width=300) 
    except:
        st.warning("Logo puo-1.png tidak ditemui")
    st.markdown("# 🏛️ SISTEM PENGURUSAN MAKLUMAT TANAH")
    st.markdown("---")
    
    # JIKA USER SALAH 3 KALI, PAPAR FORM TUKAR PASSWORD
    if st.session_state["show_reset"]:
        st.warning("⚠️ Anda telah salah kata laluan 3 kali. Sila tetapkan kata laluan baharu.")
        new_pw = st.text_input("Kata laluan baharu:", type="password")
        confirm_pw = st.text_input("Sahkan kata laluan baharu:", type="password")
        if st.button("Simpan & Log Masuk"):
            if new_pw == confirm_pw and new_pw != "":
                st.session_state["current_password"] = new_pw
                st.session_state["attempts"] = 0
                st.session_state["show_reset"] = False
                st.success("Berjaya! Sila log masuk semula.")
                st.rerun()
            else:
                st.error("Ralat! Pastikan kata laluan sepadan.")
    else:
        # Tambahan Input ID
        user_id = st.text_input("Masukkan ID Pengguna:")
        password_input = st.text_input("Masukkan kata laluan:", type="password")
        
        if st.button("Log Masuk"):
            if user_id in SENARAI_USER:
                if password_input == st.session_state["current_password"]:
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = SENARAI_USER[user_id]
                    st.session_state["attempts"] = 0
                    st.rerun()
                else:
                    st.session_state["attempts"] += 1
                    if st.session_state["attempts"] >= 3:
                        st.session_state["show_reset"] = True
                        st.rerun()
                    else:
                        st.error(f"Kata laluan salah! Baki percubaan: {3 - st.session_state['attempts']}")
            else:
                st.error("ID Pengguna tidak sah!")
    st.stop() 

# --- JIKA SUDAH LOGIN, PAPAR SISTEM UTAMA ---
st.sidebar.success(f"✅ Log Masuk Berjaya")
st.sidebar.markdown(f"### Hi, {st.session_state['user_name']}! 👋")

if st.sidebar.button("Log Keluar"):
    st.session_state["authenticated"] = False
    st.session_state["user_name"] = ""
    st.rerun()

# --- SIDEBAR ---
st.sidebar.header("🛠️ Menu Tetapan")

with st.sidebar.expander("🌍 Tetapan Peta", expanded=True):
    mod_satelit = st.toggle("Aktifkan Google Satellite", value=False)
    margin_val = st.slider("Margin Lot (Zum Keluar)", 2, 30, 10)
    
    # INPUT UNTUK EPSG CODE (Contoh: WGS84/UTM zone 47N = 32647)
    st.caption("Pilih Projeksi Grid (Contoh: WGS84/UTM zone 47N = 32647)")
    epsg_code = st.number_input("EPSG Code", value=32647)

# --- TAMBAHAN PEMILIH WARNA ---
with st.sidebar.expander("🎨 Tetapan Warna", expanded=True):
    warna_lot = st.color_picker("Pilih Warna Lot", "#000000" if not mod_satelit else "#FFFFFF")
    warna_no_stn = st.color_picker("Pilih Warna No. Stesen", "#FF0000" if not mod_satelit else "#FFFF00")

with st.sidebar.expander("🏷️ Tetapan Label", expanded=True):
    show_point = st.checkbox("Papar Point Stesen", value=True)
    saiz_point = st.slider("Saiz Point Stesen", 1, 15, 5)
    st.divider()
    show_labels = st.checkbox("Papar Label No. Stesen", value=True)
    saiz_stn = st.slider("Saiz Label Stesen", 8, 25, 12)
    st.divider()
    show_brg_dist = st.checkbox("Papar Bearing & Jarak", value=True)
    saiz_brg = st.slider("Saiz Teks Brg/Jarak", 6, 20, 10)
    st.divider()
    show_luas_center = st.checkbox("Papar Label Luas", value=True)
    saiz_luas_teks = st.slider("Saiz Label Luas", 10, 35, 18)

# --- TAJUK & LOGO UTAMA ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("puo-1.png", width=150)
    except:
        st.warning("Logo puo-1.png tidak ditemui")
with col_title:
    st.markdown(f"### 📐 Visualisasi Poligon (Hi {st.session_state['user_name']})") 
    st.caption("Jabatan Kejuruteraan Geomatik - Politeknik Ungku Omar")

st.markdown("---")

uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip() # Buang space pada nama kolum
    
    if 'E' in df.columns and 'N' in df.columns:
        luas = kira_luas(df['E'].values, df['N'].values)
        bil_garisan = len(df)
        
        # Kira Perimeter
        perimeter = 0
        for i in range(bil_garisan):
            p1 = [df.iloc[i].E, df.iloc[i].N]
            p2 = [df.iloc[(i + 1) % bil_garisan].E, df.iloc[(i + 1) % bil_garisan].N]
            _, d, _ = kira_bearing_jarak(p1, p2)
            perimeter += d
        
        # Paparan Statistik
        m1, m2, m3 = st.columns(3)
        m1.metric("Luas Poligon", f"{luas:.3f} m²")
        m2.metric("Perimeter", f"{perimeter:.3f} m")
        m3.metric("Bilangan Garisan", f"{bil_garisan}")

        # TUKAR SEMUA KOORDINAT KE LAT/LONG TERLEBIH DAHULU
        try:
            coords = df.apply(lambda row: grid_to_latlong(row['E'], row['N'], epsg_code), axis=1)
            df['lat'], df['lon'] = zip(*coords)
        except Exception as e:
            st.error(f"Ralat penukaran koordinat: {e}")
            st.stop()

        if not mod_satelit:
            # --- MOD GRID (Matplotlib) ---
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='#d3d3d3', zorder=0)
            
            x_coords = list(df['E']) + [df['E'].iloc[0]]
            y_coords = list(df['N']) + [df['N'].iloc[0]]
            ax.plot(x_coords, y_coords, color=warna_lot, linewidth=1.5, zorder=2) # TAMBAH warna_lot
            ax.fill(x_coords, y_coords, color='cyan', alpha=0.1)

            cx, cy = df['E'].mean(), df['N'].mean()

            # Point & Label Stesen
            for i, row in df.iterrows():
                if show_point:
                    ax.scatter(row['E'], row['N'], color='red', s=saiz_point*10, zorder=3)
                if show_labels:
                    vx, vy = row['E'] - cx, row['N'] - cy
                    mag = np.sqrt(vx**2 + vy**2) if np.sqrt(vx**2 + vy**2) != 0 else 1
                    ax.text(row['E'] + (vx/mag)*1.5, row['N'] + (vy/mag)*1.5, 
                            str(int(row['STN'])), fontsize=saiz_stn, fontweight='bold', ha='center', color=warna_no_stn) # TAMBAH warna_no_stn

            # Bearing & Jarak (Parallel/Rotated)
            if show_brg_dist:
                for i in range(bil_garisan):
                    p1 = [df.iloc[i].E, df.iloc[i].N]
                    p2 = [df.iloc[(i + 1) % bil_garisan].E, df.iloc[(i + 1) % bil_garisan].N]
                    
                    brg, dist_val, angle = kira_bearing_jarak(p1, p2)
                    mid_x, mid_y = (p1[0] + p2[0])/2, (p1[1] + p2[1])/2
                    
                    # BEARING - Atas garisan
                    ax.text(mid_x, mid_y, brg, color='red', fontsize=saiz_brg, 
                            ha='center', va='bottom', rotation=angle, 
                            rotation_mode='anchor', fontweight='bold')
                    
                    # JARAK - Bawah garisan
                    ax.text(mid_x, mid_y, f"{dist_val:.2f}m", color='blue', fontsize=saiz_brg, 
                            ha='center', va='top', rotation=angle, 
                            rotation_mode='anchor')

            if show_luas_center:
                ax.text(cx, cy, f"LUAS: {luas:.2f} m²", fontsize=saiz_luas_teks, 
                        fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

            ax.set_xlim(df['E'].min() - margin_val, df['E'].max() + margin_val)
            ax.set_ylim(df['N'].min() - margin_val, df['N'].max() + margin_val)
            ax.set_aspect('equal')
            ax.set_xlabel("Easting (X)")
            ax.set_ylabel("Northing (Y)")
            st.pyplot(fig)

        else:
            # --- MOD SATELIT (Folium) ---
            m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=20, max_zoom=22,
                            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google Satellite')

            # TAMBAHAN: Popup maklumat lot semasa tekan kawasan poligon
            popup_lot = folium.Popup(f"""
                <div style='font-family: Arial; width: 150px;'>
                    <h4 style='margin-bottom:5px; color:blue;'>Info Lot</h4>
                    <b>Luas:</b> {luas:.3f} m²<br>
                    <b>Perimeter:</b> {perimeter:.3f} m<br>
                    <b>Sempadan:</b> {bil_garisan} Garisan
                </div>
            """, max_width=200)

            folium.Polygon(
                locations=[[r.lat, r.lon] for i,r in df.iterrows()], 
                color=warna_lot, # TAMBAH warna_lot
                weight=2, 
                fill=True, 
                fill_opacity=0.1,
                popup=popup_lot
            ).add_to(m)
            
            m.fit_bounds([[df.lat.min(), df.lon.min()], [df.lat.max(), df.lon.max()]], padding=(margin_val, margin_val))

            # --- Label Stesen di LUAR Lot ---
            centroid_lat = df['lat'].mean()
            centroid_lon = df['lon'].mean()
            
            for i, row in df.iterrows():
                if show_point:
                    # TAMBAHAN: Popup koordinat semasa tekan stesen
                    popup_stn = folium.Popup(f"""
                        <div style='font-family: Arial; width: 130px;'>
                            <b>Stesen:</b> {int(row.STN)}<br>
                            <hr style='margin:5px 0;'>
                            <b>E:</b> {row.E:.3f}<br>
                            <b>N:</b> {row.N:.3f}<br>
                            <b>Lat:</b> {row.lat:.6f}<br>
                            <b>Lon:</b> {row.lon:.6f}
                        </div>
                    """, max_width=150)

                    folium.CircleMarker(
                        [row.lat, row.lon], 
                        radius=saiz_point, 
                        color="red", 
                        fill=True,
                        popup=popup_stn
                    ).add_to(m)
                
                if show_labels:
                    d_lat = row.lat - centroid_lat
                    d_lon = row.lon - centroid_lon
                    mag = np.sqrt(d_lat**2 + d_lon**2)
                    if mag == 0: mag = 1 
                    
                    offset_factor = 0.00001 
                    label_lat = row.lat + (d_lat / mag) * offset_factor
                    label_lon = row.lon + (d_lon / mag) * offset_factor

                    folium.map.Marker(
                        [label_lat, label_lon], 
                        icon=folium.DivIcon(html=f'''
                            <div style="
                                font-size:{saiz_stn}pt; 
                                color:{warna_no_stn}; 
                                font-weight:bold; 
                                text-shadow:2px 2px black;
                                white-space: nowrap;
                            ">
                                {int(row.STN)}
                            </div>
                        ''') # TAMBAH warna_no_stn
                    ).add_to(m)

            # --- Bearing & Jarak di Mod Satelit ---
            if show_brg_dist:
                for i in range(bil_garisan):
                    p1 = df.iloc[i]
                    p2 = df.iloc[(i + 1) % bil_garisan]
                    
                    brg_str, dist_val, txt_rot = kira_bearing_jarak([p1.E, p1.N], [p2.E, p2.N])
                    mid_lat, mid_lon = (p1.lat + p2.lat)/2, (p1.lon + p2.lon)/2
                    
                    label_html = f'''
                        <div style="
                            transform: rotate({-txt_rot}deg); 
                            white-space: nowrap; 
                            text-align: center;
                            pointer-events: none;">
                            <div style="color: #ff4d4d; font-size: {saiz_brg}pt; font-weight: bold; text-shadow: 1px 1px black; margin-bottom: -2px;">
                                {brg_str}
                            </div>
                            <div style="color: #4da6ff; font-size: {saiz_brg-1}pt; font-weight: bold; text-shadow: 1px 1px black;">
                                {dist_val:.2f}m
                            </div>
                        </div>
                    '''
                    
                    folium.Marker(
                        [mid_lat, mid_lon],
                        icon=folium.DivIcon(
                            icon_size=(150,36),
                            icon_anchor=(75,18),
                            html=label_html
                        )
                    ).add_to(m)

            # --- Luas di Tengah ---
            if show_luas_center:
                folium.map.Marker([centroid_lat, centroid_lon],
                    icon=folium.DivIcon(html=f'''
                        <div style="
                            font-size:{saiz_luas_teks}pt; 
                            color:white; 
                            font-weight:bold; 
                            text-shadow:2px 2px black;
                            background-color: rgba(0, 0, 0, 0.5);
                            border-radius: 5px;
                            padding: 5px;
                            text-align: center;
                            width: 200px;
                            transform: translate(-50%, -50%);
                        ">
                            LUAS: {luas:.2f} m²
                        </div>
                    ''')).add_to(m)

            st_folium(m, width="100%", height=650)
            
        # --- 📋 JADUAL KOORDINAT STESEN ---
        st.markdown("---")
        st.markdown("### 📋 Jadual Koordinat Stesen")
        st.dataframe(df[['STN', 'E', 'N', 'lat', 'lon']], use_container_width=True)

        # --- EKSPORT DATA ---
        st.sidebar.divider()
        if st.sidebar.button("🌍 Sediakan Fail Eksport"):
            poly_coords = [[row.lon, row.lat] for i,row in df.iterrows()]
            poly_coords.append(poly_coords[0])
            
            polygon_feature = {
                "type": "Feature",
                "properties": {
                    "Name": "Lot Tanah",
                    "Luas_m2": round(luas, 3), 
                    "Perimeter_m": round(perimeter, 3)
                },
                "geometry": {
                    "type": "Polygon", 
                    "coordinates": [poly_coords]
                }
            }
            
            point_features = []
            for i, row in df.iterrows():
                point_feature = {
                    "type": "Feature",
                    "properties": {
                        "Name": f"Stesen {int(row.STN)}",
                        "E": row.E,
                        "N": row.N
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row.lon, row.lat]
                    }
                }
                point_features.append(point_feature)
            
            all_features = [polygon_feature] + point_features
            geojson_data = {
                "type": "FeatureCollection",
                "features": all_features
            }
            
            st.sidebar.download_button(
                label="📥 Muat Turun GeoJSON (QGIS)",
                data=json.dumps(geojson_data, indent=4),
                file_name="lot_puo.geojson",
                mime="application/json"
            )

else:
    st.info("Sila muat naik fail CSV untuk memulakan.")
