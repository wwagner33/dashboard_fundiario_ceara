# modules/mapa_interativo.py

"""
Funções para gerar o mapa interativo:
- preprocessar_tudo(df_inter)
- criar_mapa_com_camadas(gdf_inter, sel_regiao)
"""

import folium
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import wkt

CORES = {
    'Minifúndio': '#9b19f5',
    'Pequena Propriedade': '#0040bf',
    'Média Propriedade': '#e6d800',
    'Grande Propriedade': '#d97f00',
    'Sem Classificação': '#808080'
}

def preprocessar_tudo(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Filtra registros com geometria válida e retorna GeoDataFrame em EPSG:4326.
    """
    df_valid = df[df['geometry'].notna()].copy()
    return gpd.GeoDataFrame(df_valid, geometry='geometry', crs='EPSG:4326')


def criar_mapa_com_camadas(gdf: gpd.GeoDataFrame, sel_regiao: str) -> folium.Map:
    """
    Cria um mapa Folium centrado na região selecionada,
    adicionando camadas por categoria de propriedade.
    Corrige geometrias inválidas antes de calcular o centroide.
    """
    # Filtra pela região administrativa
    gdf_reg = gdf[gdf['regiao_administrativa'] == sel_regiao].copy()
    if gdf_reg.empty:
        raise ValueError(f"Região '{sel_regiao}' sem dados para plotagem.")

    # Corrige possíveis geometrias inválidas
    gdf_reg['geometry'] = gdf_reg['geometry'].buffer(0)

    # Centra no centroid da união das geometrias corrigidas
    centro = gdf_reg.geometry.unary_union.centroid
    mapa = folium.Map(location=[centro.y, centro.x], zoom_start=10)

    # Cria FeatureGroup por categoria
    grupos = {}
    for categoria in sorted(gdf['categoria'].unique()):
        fg = folium.FeatureGroup(name=categoria, show=True)
        mapa.add_child(fg)
        grupos[categoria] = fg

    # Adiciona geometria a cada camada
    for _, row in gdf_reg.iterrows():
        cor = CORES.get(row['categoria'], CORES['Sem Classificação'])
        folium.GeoJson(
            row.geometry,
            style_function=lambda feat, color=cor: {
                'fillColor': color,
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0.7
            }
        ).add_to(grupos[row['categoria']])

    # Controle de camadas
    folium.LayerControl().add_to(mapa)
    return mapa
