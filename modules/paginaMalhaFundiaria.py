# modules/paginaMalhaFundiaria.py
"""Página Mapa da Malha Fundiária: polígonos dos imóveis por categoria de tamanho.

O nome do proprietário só aparece quando a LGPD permite (ver ``privacidade``).
O mascaramento é feito aqui, antes de montar o mapa, então o nome de pessoa
física não chega ao navegador.
"""

import folium
import streamlit as st

from modules import repositorio
from modules.apiCliente import ErroApi
from modules.camadasMapa import adicionarCamadaMunicipios, adicionarControles, criarMapaBase, renderizarMapa, rotuloLegenda
from modules.componentesUi import cabecalhoFiltros, mostrarErroDados, paragrafoInformativo
from modules.constantes import CENTRO_CEARA
from modules.privacidade import escaparHtml, nomeProprietarioExibivel
from public.cores import CORES

TODA_REGIAO = "(toda a região)"
CAMPOS_TOOLTIP = [
    ("imovel", "Nome:"),
    ("nome_proprietario", "Nome do Proprietário:"),
    ("data_criacao_lote", "Data de Criação:"),
    ("numero_incra", "N° Incra:"),
    ("numero_lote", "N° Lote:"),
    ("area", "Área (ha):"),
    ("situacao_juridica", "Situação Jurídica:"),
    ("regiao_administrativa", "Região Administrativa:"),
    ("nome_municipio_original", "Município:"),
    ("categoria", "Categoria:"),
]
ESTILO_LIMITES = {"color": "#003366", "weight": 2, "opacity": 0.8, "dashArray": "5, 5"}
ROTULO_LIMITES = (
    '<span><svg width="12" height="12"><rect width="12" height="12" fill="#003366"/></svg> '
    "Limites Municipais</span>"
)


def prepararLotesParaMapa(geojson: dict) -> dict[str, dict]:
    """Separa os imóveis por categoria e deixa só os campos do tooltip.

    O nome do proprietário passa por ``nomeProprietarioExibivel`` e todo texto
    é escapado. Imóveis sem categoria conhecida ficam de fora, como antes.
    """
    grupos: dict[str, list] = {categoria: [] for categoria in CORES}
    for feature in geojson.get("features", []):
        origem = feature.get("properties") or {}
        categoria = origem.get("categoria") or "Sem Classificação"
        if categoria not in grupos:
            continue
        propriedades = {campo: escaparHtml(origem.get(campo)) for campo, _ in CAMPOS_TOOLTIP}
        propriedades["nome_proprietario"] = escaparHtml(nomeProprietarioExibivel(origem.get("nome_proprietario")))
        grupos[categoria].append({"type": "Feature", "geometry": feature.get("geometry"), "properties": propriedades})
    return {cat: {"type": "FeatureCollection", "features": feats} for cat, feats in grupos.items() if feats}


def obterCentroMapa(geojson: dict) -> list:
    """Primeiro vértice do primeiro polígono, ou o centro do Ceará."""
    for feature in geojson.get("features", []):
        geometria = feature.get("geometry") or {}
        try:
            if geometria.get("type") == "Polygon":
                lon, lat = geometria["coordinates"][0][0][:2]
                return [lat, lon]
            if geometria.get("type") == "MultiPolygon":
                lon, lat = geometria["coordinates"][0][0][0][:2]
                return [lat, lon]
        except (IndexError, TypeError, ValueError):
            continue
    return CENTRO_CEARA


def criarMapaMalha(grupos: dict[str, dict], limites: dict, centro: list) -> folium.Map:
    mapa = criarMapaBase(centro=centro, zoom=9, estilo="voyager")
    adicionarCamadaMunicipios(mapa, limites, nome=ROTULO_LIMITES, estilo=ESTILO_LIMITES)
    campos = [c for c, _ in CAMPOS_TOOLTIP]
    aliases = [a for _, a in CAMPOS_TOOLTIP]
    for categoria, colecao in grupos.items():
        cor = CORES[categoria]
        grupo = folium.FeatureGroup(name=rotuloLegenda(cor, categoria, forma="circulo"), overlay=True, control=True)
        folium.GeoJson(
            colecao,
            style_function=lambda _, cor=cor: {"fillColor": cor, "color": "#000", "weight": 0.5, "fillOpacity": 0.6},
            tooltip=folium.GeoJsonTooltip(fields=campos, aliases=aliases, localize=True),
        ).add_to(grupo)
        grupo.add_to(mapa)
    adicionarControles(mapa)
    return mapa


def renderizar() -> None:
    try:
        regioes = repositorio.carregarRegioes()
    except ErroApi:
        mostrarErroDados()
        return
    if not regioes:
        st.error("Nenhuma região administrativa disponível.")
        return

    col1, col2 = st.columns([8, 3])
    with col2:
        paragrafoInformativo(
            "Este mapa apresenta a distribuição das propriedades rurais por categoria de tamanho "
            "(Pequena < 1 MF, Pequena, Média e Grande). </br></br>"
            "As regiões em branco no mapa, são correspondentes às áreas urbanas ou áreas rurais ainda não regularizadas."
        )
        cabecalhoFiltros()
        paragrafoInformativo(
            "O sistema é capaz de filtrar por Estado, Município ou Região Administrativa. "
            "Exibindo tanto a quantidade de propriedades quanto a proporção de área ocupada "
            "por cada categoria, conforme o recorte desejado.",
            estilo="padding-bottom: 16px",
        )
        regiao = st.selectbox("Selecione a Região administrativa", regioes)
        try:
            municipios = repositorio.carregarMunicipiosDaRegiao(regiao)
        except ErroApi:
            municipios = []
        municipio = st.selectbox("Selecione o Município", [TODA_REGIAO] + municipios)

    try:
        if municipio == TODA_REGIAO:
            geojson = repositorio.carregarGeojsonLotes(regiao=regiao)
            alvoLimites = municipios
        else:
            geojson = repositorio.carregarGeojsonLotes(municipio=municipio)
            alvoLimites = [municipio]
        limites = repositorio.filtrarLimites(repositorio.carregarLimitesMunicipais(), alvoLimites)
    except ErroApi:
        with col1:
            mostrarErroDados()
        return

    if not geojson.get("features"):
        col1.warning("Nenhuma geometria encontrada.")
        return

    mapa = criarMapaMalha(prepararLotesParaMapa(geojson), limites, obterCentroMapa(geojson))
    with col1, st.spinner("Gerando mapa..."):
        renderizarMapa(mapa)
