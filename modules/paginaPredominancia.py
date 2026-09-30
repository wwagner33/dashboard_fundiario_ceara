# modules/paginaPredominancia.py
"""Página Mapa de Predominância: categoria de imóvel mais frequente em cada município."""

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from branca.element import MacroElement, Template
from folium.plugins import Fullscreen, HeatMap, MiniMap

from modules import config, repositorio
from modules.apiCliente import ErroApi
from modules.camadasMapa import adicionarCamadaMunicipios, criarMapaBase, renderizarMapa
from modules.classificacao import CATEGORIAS
from modules.componentesUi import mostrarErroDados, paragrafoInformativo
from modules.constantes import CRS_GEOGRAFICO, CRS_METRICO
from modules.privacidade import escaparColunasTexto
from public.cores import CORES

MODO_CALOR = "Mapa de Calor"
MODO_PREDOMINANTE = "Tipo de Propriedade Predominante no Município"
SEM_REGISTROS = "Sem Registros"
CENTRO_MAPA = [-5.4984, -39.3200]


def prepararDados(
    dfLotes: pd.DataFrame, limites: gpd.GeoDataFrame, categorias: list[str] = CATEGORIAS
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Conta os imóveis por município e categoria e indica a categoria dominante.

    A tabela inclui todos os municípios dos limites, mesmo os que não têm
    imóveis cadastrados, com contagem zero e dominante "Sem Registros".
    """
    municipios = sorted(set(limites["nome_municipio"].dropna()) | set(dfLotes["nome_municipio"].dropna()))
    contagem = dfLotes.groupby(["nome_municipio", "categoria"]).size()
    tabela = contagem.unstack(fill_value=0) if not contagem.empty else pd.DataFrame()
    tabela = tabela.reindex(index=municipios, columns=categorias, fill_value=0).astype(int)
    tabela.index.name = "nome_municipio"

    tabela["total"] = tabela[categorias].sum(axis=1)
    comDados = tabela["total"] > 0
    tabela["dominante"] = tabela[categorias].idxmax(axis=1).where(comDados, SEM_REGISTROS)
    tabela["prop_dom"] = (tabela[categorias].max(axis=1) / tabela["total"].where(comDados, 1)).where(comDados, 0.0)

    dfTabular = tabela.reset_index()
    gdfGeo = limites[["nome_municipio", "geometry"]].merge(dfTabular, on="nome_municipio", how="left")
    return gpd.GeoDataFrame(gdfGeo, geometry="geometry", crs=limites.crs), dfTabular


@st.cache_resource(ttl=config.TTL_DADOS, show_spinner=False, max_entries=2)
def _prepararDadosCache(versao: float, idLimites: int, _lotes: pd.DataFrame, _limites: gpd.GeoDataFrame):
    return prepararDados(_lotes, _limites)


def _adicionarLegenda(mapa: folium.Map, cores: dict) -> None:
    legenda = """
    {% macro html(this, kwargs) %}
    <div id='legend' style="
       position: fixed; top: 10px; right: 10px;
       width: 220px; background: white; padding: 10px;
       border:2px solid grey; z-index:9999;
       font-size:12px; line-height:1.2em;">
      <b>Classificação dos Lotes</b><br>
      {% for cat, color in this.cores.items() %}
        <i style="background:{{color}};width:18px;height:14px;
                  display:inline-block;margin-right:8px;"></i>{{cat}}<br>
      {% endfor %}
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(legenda)
    macro.cores = cores
    mapa.get_root().add_child(macro)


def criarMapaPredominancia(
    gdf: gpd.GeoDataFrame, modo: str = MODO_PREDOMINANTE, categoriaCalor: str | None = None,
    limites: dict | None = None, cores: dict = CORES,
) -> folium.Map:
    mapa = criarMapaBase(centro=CENTRO_MAPA, zoom=7, prefer_canvas=False)
    if modo == MODO_CALOR and categoriaCalor in gdf.columns:
        adicionarCamadaMunicipios(
            mapa, limites, nome="Limite dos Municípios", estilo={"color": "#888", "weight": 3, "fillOpacity": 0}
        )
        centros = gdf.geometry.to_crs(CRS_METRICO).centroid.to_crs(CRS_GEOGRAFICO)
        pontos = [
            [ponto.y, ponto.x, float(peso)]
            for ponto, peso in zip(centros, gdf[categoriaCalor], strict=True)
            if peso > 0 and ponto is not None and not ponto.is_empty
        ]
        if pontos:
            HeatMap(
                pontos, min_opacity=0.3, max_opacity=0.9, radius=35, blur=18,
                gradient={0.0: "#ffffff", 1.0: cores.get(categoriaCalor, "#fd8d3c")},
                name=f"Mapa de Calor: {categoriaCalor}",
            ).add_to(mapa)
    else:
        dados = escaparColunasTexto(gdf[["nome_municipio", "dominante", "geometry"]], ["nome_municipio"])
        folium.GeoJson(
            dados,
            style_function=lambda feature: {
                "fillColor": cores.get(feature["properties"].get("dominante"), cores[SEM_REGISTROS]),
                "color": "black",
                "weight": 0.4,
                "fillOpacity": 0.8,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["nome_municipio", "dominante"], aliases=["Município:", "Tipo Dominante:"],
                localize=True, labels=True, sticky=False,
            ),
            name="Categorias Dominantes",
        ).add_to(mapa)
    _adicionarLegenda(mapa, cores)
    MiniMap(toggle_display=True).add_to(mapa)
    Fullscreen().add_to(mapa)
    return mapa


def tabelaDoMunicipio(dfTabular: pd.DataFrame, municipio: str) -> pd.DataFrame:
    """Quantidade de imóveis por categoria de um município, com zeros se não houver cadastro."""
    linha = dfTabular[dfTabular["nome_municipio"] == municipio]
    colunas = CATEGORIAS + ["total"]
    valores = linha.iloc[0][colunas].astype(int) if not linha.empty else pd.Series(0, index=colunas)
    return (
        valores.rename({"Pequena Propriedade < 1 MF": "Pequena <1MF", "total": "Total"})
        .rename_axis("Categoria")
        .to_frame("Quantidade de Imóveis")
    )


def renderizar() -> None:
    try:
        lotes = repositorio.carregarLotesClassificados()
        limites = repositorio.carregarLimitesMunicipaisGdf()
        limitesGeojson = repositorio.carregarLimitesMunicipais()
    except ErroApi:
        mostrarErroDados()
        return
    gdfGeo, dfTabular = _prepararDadosCache(repositorio.versaoDados(lotes), id(limites), lotes, limites)
    totais = dfTabular.set_index("nome_municipio")["total"]

    col1, col2 = st.columns([7, 3])
    with col2:
        paragrafoInformativo("Este mapa identifica a categoria fundiária predominante em cada município do Ceará.")
        modo = st.radio("Tipo de Mapa:", options=[MODO_CALOR, MODO_PREDOMINANTE], index=0)
        paragrafoInformativo(
            "É possível visualizar tanto a predominância por cor, quanto a intensidade de cada "
            "categoria (mapa de calor)."
        )
        categoriaCalor = st.selectbox("Categoria para Mapa de Calor:", CATEGORIAS) if modo == MODO_CALOR else None

        st.markdown("#### Classificação do Município")
        municipio = st.selectbox(
            "Selecione o município",
            options=sorted(gdfGeo["nome_municipio"].dropna().unique()),
            format_func=lambda x: f"{x} ({'com dados' if totais.get(x, 0) > 0 else 'sem dados'})",
        )
        st.dataframe(tabelaDoMunicipio(dfTabular, municipio), width="stretch")

    with col1:
        mapa = criarMapaPredominancia(gdfGeo, modo, categoriaCalor, limitesGeojson)
        renderizarMapa(mapa)
