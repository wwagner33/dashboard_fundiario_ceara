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
from shapely.ops import unary_union
from shapely.geometry import Point

# ————————————————————————————————————————————————————————————————————
# Configuração de cores por categoria
from public.cores import CORES as cores

CORES = cores
CORES["Sem Classificação"] = "#808080"

# ————————————————————————————————————————————————————————————————————
def carregar_dados_por_regiao(data: pd.DataFrame, regiao: str) -> gpd.GeoDataFrame:
    """Filtra e prepara os dados para a região especificada."""
    df = data[
        (data['regiao_administrativa'] == regiao) &
        data['geom'].notna() &
        data['geom'].apply(lambda x: isinstance(x, str))
    ].copy()
    if df.empty:
        raise ValueError(f"Nenhum dado válido encontrado para: {regiao}")
    return df

# ————————————————————————————————————————————————————————————————————
def preprocessar_tudo(df_raw: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    1) Filtra os dados válidos
    2) Converte WKT para Shapely
    3) Converte para GeoDataFrame
    4) Classifica todas as propriedades
    5) Retorna um GeoDataFrame COMPLETO pronto pra filtrar por região.
    """
    df = df_raw[df_raw['geom'].notna() & df_raw['geom'].apply(lambda x: isinstance(x, str))].copy()

    # converte string WKT em shapely
    def to_geom(w):
        try:
            return wkt.loads(w)
        except:
            return None

    df['geometry'] = df['geom'].map(to_geom)
    df = df[df['geometry'].notna()]

    # monta GeoDataFrame e projeta
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:31984')
    gdf = gdf.to_crs(epsg=4326)

    # Classificação
    conds = [
        (gdf['area'] > 0) & (gdf['area'] < gdf['modulo_fiscal']),
        (gdf['area'] >= gdf['modulo_fiscal']) & (gdf['area'] <= 4 * gdf['modulo_fiscal']),
        (gdf['area'] > 4 * gdf['modulo_fiscal']) & (gdf['area'] <= 15 * gdf['modulo_fiscal']),
        (gdf['area'] > 15 * gdf['modulo_fiscal'])
    ]
    cats = list(CORES.keys())[:-1]
    gdf['categoria'] = np.select(conds, cats, default="Sem Classificação")

    return gdf


# def criar_mapa_com_camadas(gdf: gpd.GeoDataFrame, regiao: str) -> folium.Map:
#     """Gera um mapa Folium com camadas por categoria para a região especificada."""
#     # Projeta para cálculo de centro e remove geometrias vazias
#     gdf_proj = gdf.to_crs(epsg=31983)
#     gdf_proj = gdf_proj[~gdf_proj.geometry.is_empty]
#     if gdf_proj.empty:
#         raise ValueError(f"Sem geometrias válidas para calcular o centro em: {regiao}")

#     # calcula centroide da união de geometrias
#     union_geom = unary_union(gdf_proj.geometry)
#     centro_proj = union_geom.centroid
#     centro_wgs84 = gpd.GeoSeries([centro_proj], crs='EPSG:31983').to_crs(epsg=4326)[0]

#     # inicia mapa centrado
#     m = folium.Map(
#         location=[centro_wgs84.y, centro_wgs84.x],
#         zoom_start=10,
#         width="95%",
#         height="800px"
#     )

#     # cria grupo para cada categoria
#     grupos = {cat: folium.FeatureGroup(name=cat) for cat in CORES.keys()}
#     for fg in grupos.values():
#         m.add_child(fg)

#     # adiciona geometrias filtradas
#     region_gdf = gdf[gdf['regiao_administrativa'] == regiao]
#     for _, row in region_gdf.iterrows():
#         fg = grupos.get(row['categoria'])
#         if fg and hasattr(row.geometry, 'geom_type'):
#             folium.GeoJson(
#                 row.geometry,
#                 style_function=lambda feat, cat=row['categoria']: {
#                     'fillColor': CORES[cat],
#                     'color': 'black',
#                     'weight': 0.5,
#                     'fillOpacity': 0.7
#                 },
#                 tooltip=folium.Tooltip(
#                     html=(
#                         f"<strong>Nome:</strong> {row.get('imovel', '')}<br>"
#                         f"<strong>INCRA:</strong> {row.get('numero_incra', '')}<br>"
#                         f"<strong>Situação:</strong> {row.get('situacao_juridica', '')}<br>"
#                         f"<strong>Município:</strong> {row.get('nome_municipio', '')}<br>"
#                         f"<strong>Distrito:</strong> {row.get('distrito', '')}<br>"
#                         f"<strong>Área:</strong> {row['area']} ha<br>"
#                         f"<strong>Categoria:</strong> {row['categoria']}"
#                     )
#                 )
#             ).add_to(fg)

#     # legenda estática
#     legend = f"""
#       <div style="position: fixed; top: 150px; right: 150px; z-index:1000;
#                   background:white; padding:10px; border:2px solid grey;
#                   border-radius:5px; font-size:14px;">
#         <strong>{regiao}</strong><br>
#         {'<br>'.join([f'<i style="color:{c}">■</i> {cat}' for cat,c in CORES.items()])}
#       </div>
#     """
#     m.get_root().html.add_child(folium.Element(legend))

#     # controle de camadas
#     folium.LayerControl(collapsed=True).add_to(m)

#     return m
def criar_mapa_com_camadas(gdf: gpd.GeoDataFrame, regiao: str) -> folium.Map:
    """
    Gera um mapa Folium com camadas por categoria para a região especificada,
    corrigindo geometrias inválidas e usando fallback de bounding box se necessário.
    """
    # 1) Projeta para cálculo e remove geometrias vazias
    gdf_proj = gdf.to_crs(epsg=31983)
    gdf_proj = gdf_proj[~gdf_proj.geometry.is_empty]
    if gdf_proj.empty:
        raise ValueError(f"Sem geometrias válidas para calcular o centro em: {regiao}")

    # 2) Tenta corrigir geometrias inválidas e fazer o union
    try:
        geoms_fixed = gdf_proj.geometry.apply(
            lambda g: g.buffer(0) if not g.is_valid else g
        )
        union_geom = unary_union(geoms_fixed)
        centro_proj = union_geom.centroid
    except Exception:
        # Fallback: usa bounding box
        xmin, ymin, xmax, ymax = gdf_proj.total_bounds
        centro_proj = Point((xmin + xmax) / 2, (ymin + ymax) / 2)

    # 3) Transforma o ponto central para WGS84
    centro_wgs84 = (
        gpd.GeoSeries([centro_proj], crs="EPSG:31983")
           .to_crs(epsg=4326)[0]
    )

    # 4) Inicia o mapa centrado
    m = folium.Map(
        location=[centro_wgs84.y, centro_wgs84.x],
        zoom_start=10,
        width="95%",
        height="800px"
    )

    # 5) Cria um FeatureGroup para cada categoria
    grupos = {cat: folium.FeatureGroup(name=cat) for cat in CORES.keys()}
    for fg in grupos.values():
        m.add_child(fg)

    # 6) Adiciona as geometrias da região selecionada
    region_gdf = gdf[gdf["regiao_administrativa"] == regiao]
    for _, row in region_gdf.iterrows():
        fg = grupos.get(row["categoria"])
        if fg:
            folium.GeoJson(
                row.geometry,
                style_function=lambda feat, cat=row["categoria"]: {
                    "fillColor": CORES[cat],
                    "color": "black",
                    "weight": 0.5,
                    "fillOpacity": 0.7
                },
                popup=folium.Popup(
                    html=(
                        f"<strong>Nome:</strong> {row.get('imovel','')}<br>"
                        f"<strong>INCRA:</strong> {row.get('numero_incra','')}<br>"
                        f"<strong>Situação:</strong> {row.get('situacao_juridica','')}<br>"
                        f"<strong>Município:</strong> {row.get('nome_municipio','')}<br>"
                        f"<strong>Distrito:</strong> {row.get('distrito','')}<br>"
                        f"<strong>Área:</strong> {row['area']} ha<br>"
                        f"<strong>Categoria:</strong> {row['categoria']}"
                    )
                )
            ).add_to(fg)

    # 7) Adiciona legenda estática
    legend = f"""
    <div style="
        position: fixed; top: 150px; right: 150px; z-index:1000;
        background:white; padding:10px; border:2px solid grey;
        border-radius:5px; font-size:14px;">
      <strong>{regiao}</strong><br>
      {'<br>'.join([f'<i style="color:{c}">■</i> {cat}' for cat,c in CORES.items()])}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend))

    # 8) Controla as camadas
    folium.LayerControl(collapsed=True).add_to(m)

    return m