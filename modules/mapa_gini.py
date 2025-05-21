import streamlit as st
import pandas as pd
import geopandas as gpd
import unicodedata
import folium
import numpy as np
import os
from datetime import datetime
from folium.features import GeoJsonTooltip
from shapely.geometry import Polygon, MultiPolygon
from streamlit_folium import st_folium

# ——————————————————————————————————————————————
# Configurações iniciais
st.set_page_config(layout="wide")
st.title("Mapa de Gini da Malha Fundiária do Ceará")

@st.cache_data
def load_data():
    df = pd.read_csv(
        "data/dataset-malha-fundiaria-idace_preprocessado-2025-04-26.csv",
        low_memory=False
    )
    gdf = gpd.read_file(
        "data/geojson-municipios_ceara-normalizado.geojson"
    )
    return df, gdf

# Normalização de nomes

def normalizar_nome(nome):
    if not isinstance(nome, str): return nome
    s = unicodedata.normalize('NFKD', nome).encode('ASCII','ignore').decode()
    return s.lower().replace(" ", "_").upper()

# Cálculo de Gini

def gini(arr):
    a = np.sort(np.array(arr, dtype=float))
    a = a[a >= 0]
    n = a.size
    if n == 0: return float('nan')
    idx = np.arange(1, n+1)
    return (2 * np.sum(idx * a) / (n * np.sum(a))) - (n+1)/n

# Carrega dados

df_props, municipios = load_data()

# Detecta outliers via IQR para uso interno
areas = df_props['area']
Q1, Q3 = areas.quantile([0.25,0.75])
IQR = Q3 - Q1
out_iqr = df_props[(areas < Q1 - 1.5*IQR) | (areas > Q3 + 1.5*IQR)]

# Detecta áreas absurdas: ≥ metade do estado
# HALF_STATE_HA = 1488860 / 2  # ~744430 ha
# out_err = df_props[df_props['area'] >= HALF_STATE_HA]
HALF_STATE_HA = 1488860 / 2  # ~744430 ha
out_err = df_props[
    (df_props['area'] >= HALF_STATE_HA) |
    (df_props['lote_id'] == 8601)
]

# Salva somente áreas absurdas em CSV
os.makedirs('removed_registers', exist_ok=True)
date_str = datetime.now().strftime('%Y-%m-%d')
removed_file = f"removed_registers/gini_removed_{date_str}.csv"
out_err.to_csv(removed_file, index=False)

# Prepara DataFrames para cálculos
df_with = df_props.copy()
df_no = df_props.drop(pd.concat([out_iqr, out_err]).drop_duplicates().index)

# Normaliza nomes
for df in [df_with, df_no]:
    df['nome_municipio_original'] = df['nome_municipio']
    df['nome_municipio'] = df['nome_municipio'].apply(normalizar_nome)
municipios['nome_municipio'] = municipios['NM_MUN'].apply(normalizar_nome)
muni_geo = municipios.rename(columns={'nome_municipio':'nome_municipio'})

# Conta lotes por município para warnings
df_with['cnt'] = df_with.groupby('nome_municipio')['area'].transform('count')
df_no['cnt'] = df_no.groupby('nome_municipio')['area'].transform('count')
warning_munis = df_with[df_with['cnt'] == 1]['nome_municipio'].unique().tolist()

# Geração DataFrame de Gini por município
def calc_gini_df(df):
    return df.groupby('nome_municipio').agg(
        nome_municipio_original=('nome_municipio_original','first'),
        regiao_administrativa=('regiao_administrativa','first'),
        cnt=('cnt','first'),
        gini_area=('area', lambda x: gini(x.values))
    ).reset_index()
gini_with = calc_gini_df(df_with)
gini_no = calc_gini_df(df_no)

# Filtra warnings do DataFrame de tabelas
gini_with_filt = gini_with[gini_with['cnt'] > 1]
gini_no_filt   = gini_no[gini_no['cnt'] > 1]

# Cálculo de Gini estadual sem warnings mas incluindo outliers
state_no_warn = gini(df_with[~df_with['nome_municipio'].isin(warning_munis)]['area'].values)

# Merge GeoJSON + Gini
geo_with = muni_geo.merge(gini_with, on='nome_municipio', how='left')
geo_no   = muni_geo.merge(gini_no,   on='nome_municipio', how='left')

# Estilo de polígonos
def style_fn(f):
    p = f['properties']
    if p.get('cnt') == 1:
        return {'fillColor':'#FFD700','color':'black','weight':0.5,'fillOpacity':0.8}
    g = p.get('gini_area')
    if pd.isna(g): return {'fillColor':'#D3D3D3','color':'black','weight':0.5,'fillOpacity':0.8}
    if g <= 0.700: c='#f9c0ba'
    elif g <= 0.800: c='#d8948c'
    elif g <= 0.850: c='#b66960'
    elif g <= 0.900: c='#923f37'
    else: c='#6e1111'
    return {'fillColor':c,'color':'black','weight':0.5,'fillOpacity':0.8}

# Abas
tabs = st.tabs([
    'Mapa com Gini por município', 
    'Tabela Gini por município',
    'Gini do Estado', 'Lotes Excluídos'
])

# Renderização de mapas
def render_map(tab, geo_df):
    with tab:
        m = folium.Map(location=[-5.2,-39.5], zoom_start=8, tiles='cartodbpositron')
        tooltip = GeoJsonTooltip(fields=['nome_municipio_original','gini_area','cnt'],
                                 aliases=['Município','Índice de Gini','# Lotes'],
                                 localize=True, sticky=True)
        folium.GeoJson(geo_df, style_function=style_fn, tooltip=tooltip).add_to(m)
        for _, row in geo_df.iterrows():
            geom = row.geometry
            if isinstance(geom, (Polygon, MultiPolygon)):
                c = geom.centroid
                folium.map.Marker([c.y,c.x], icon=folium.DivIcon(
                    html=f"""<div style='font-size:6pt; font-weight:bold; color:black; text-shadow:0 0 4px white;'>{row['nome_municipio']}</div>""")).add_to(m)
        # Adiciona aviso de lotes únicos
        legend_html = """
                <div style='position:fixed;top:10px;right:10px;background:white;padding:10px;border:1px solid grey;font-size:14px;z-index:9999;'>
                <b>Intervalos de Gini</b><br>
                <i style='background:#FFD700;width:12px;height:12px;float:left;margin-right:4px'></i>1 lote (warning)<br>
                <i style='background:#f9c0ba;width:12px;height:12px;float:left;margin-right:4px'></i>≤0.700<br>
                <i style='background:#d8948c;width:12px;height:12px;float:left;margin-right:4px'></i>0.701–0.800<br>
                <i style='background:#b66960;width:12px;height:12px;float:left;margin-right:4px'></i>0.801–0.850<br>
                <i style='background:#923f37;width:12px;height:12px;float:left;margin-right:4px'></i>0.851–0.900<br>
                <i style='background:#6e1111;width:12px;height:12px;float:left;margin-right:4px'></i>>0.900<br>
                <i style='background:#D3D3D3;width:12px;height:12px;float:left;margin-right:4px'></i>Sem dados
                </div>"""
        m.get_root().html.add_child(folium.Element(legend_html))
        st_folium(m, width=1100, height=900)

# Renderiza mapas
render_map(tabs[0], geo_with)

# Tabelas
with tabs[1]:
    st.subheader('Tabela Gini por município')
    st.dataframe(
        gini_with_filt[['regiao_administrativa','nome_municipio_original','cnt','gini_area']]
        .rename(columns={'regiao_administrativa':'Região','nome_municipio_original':'Município','cnt':'# Lotes','gini_area':'Gini'}),
        use_container_width=True
    )

# Gini estadual e notas
with tabs[2]:
    st.subheader('Índice de Gini ')
    st.metric('do Estado do Ceará', f"{state_no_warn:.4f}")


with tabs[3]:
    st.subheader('Lotes Excluídos')
    out_disp = out_err[['lote_id','nome_municipio_original','regiao_administrativa','area']].copy()
    out_disp['Área'] = out_disp['area'].map(lambda x: str(x).replace('.', ','))
    st.dataframe(
        out_disp.rename(columns={'lote_id':'Lote ID','nome_municipio_original':'Município','regiao_administrativa':'Região'})
        [['Lote ID','Município','Região','Área']],
        use_container_width=True
    )

