# modules/mapa_contextual.py

import folium
import geopandas as gpd
import pandas as pd


def preparar_dados(df_ctx: pd.DataFrame, muni_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Agrega contagens por município (df_ctx), mescla com muni_gdf
    e calcula para cada município: total e categoria dominante.
    """
    tbl = (
        df_ctx
        .groupby(['municipio_norm','categoria'])
        .size()
        .unstack(fill_value=0)
    )
    tbl['total']     = tbl.sum(axis=1)
    tbl['dominante'] = tbl.drop(columns=['total']).idxmax(axis=1)
    tbl = tbl.reset_index()

    gdf = muni_gdf.merge(tbl, on='municipio_norm', how='left')

    for col in ['Minifúndio','Pequena Propriedade','Média Propriedade','Grande Propriedade','total']:
        gdf[col] = gdf.get(col, 0).fillna(0)
    gdf['dominante'] = gdf['dominante'].fillna('Sem Dados')

    return gdf.set_geometry('geometry')


def criar_choropleth_contextual(gdf: gpd.GeoDataFrame) -> folium.Map:
    """
    Retorna um folium.Map com choropleth da coluna 'total'
    e tooltip exibindo ['nome_municipio','total','dominante'].
    """
    centro = [-5.4984, -39.3200]
    mapa = folium.Map(location=centro, zoom_start=7)

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=['nome_municipio','total'],
        key_on='feature.properties.nome_municipio',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Total de Propriedades',
    ).add_to(mapa)

    folium.GeoJson(
        gdf,
        style_function=lambda feat: {'fillColor':'transparent','color':'black','weight':0.5},
        tooltip=folium.features.GeoJsonTooltip(
            fields=['nome_municipio','total','dominante'],
            aliases=['Município','Total','Categoria Dominante'],
            localize=True
        )
    ).add_to(mapa)

    return mapa
