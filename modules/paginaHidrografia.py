# modules/paginaHidrografia.py
"""Página Mapa Hidrográfico: reservatórios monitorados, com municípios e assentamentos de contexto."""

import folium
import streamlit as st
from folium.plugins import MarkerCluster
from shapely.geometry import shape

from modules import repositorio
from modules.apiCliente import ErroApi
from modules.camadasMapa import (
    adicionarCamadaMunicipios, adicionarCamadasAssentamentos, adicionarControles,
    criarMapaBase, formatarValor, renderizarMapa, rotuloLegenda,
)
from modules.componentesUi import cabecalhoFiltros, mostrarErroDados, paragrafoInformativo
from modules.constantes import COR_RESERVATORIO, TOLERANCIA_ASSENTAMENTOS
from modules.privacidade import escaparHtml

TODOS = "Todos"
CAMPOS_RESERVATORIO = [
    ("id_sagreh", "ID"), ("nome", "Nome"), ("proprietario", "Proprietário"), ("gerencia", "Gerência"),
    ("reg_hidrog", "Região Hidro"), ("nome_municipio_original", "Município"), ("ano_constr", "Ano"),
    ("ri", "Rio ou Riacho"), ("o_barrad", "Barragem"), ("area_ha", "Área (ha)"), ("capacid_m3", "Capacidade (m³)"),
]


def calcularEstatisticas(geojson: dict | None) -> dict:
    """Quantidade, capacidade total (m³) e área total (ha), ignorando valores inválidos."""
    features = (geojson or {}).get("features", [])
    capacidades, areas = [], []
    for feature in features:
        propriedades = feature.get("properties", {})
        for campo, destino in (("capacid_m3", capacidades), ("area_ha", areas)):
            try:
                destino.append(float(propriedades.get(campo, 0)))
            except (TypeError, ValueError):
                pass
    return {"total": len(features), "capacidadeTotalM3": sum(capacidades), "areaTotalHa": sum(areas)}


def _prepararReservatorio(feature: dict) -> dict:
    origem = feature.get("properties") or {}
    propriedades = {campo: escaparHtml(formatarValor(origem.get(campo))) for campo, _ in CAMPOS_RESERVATORIO}
    return {"type": "Feature", "geometry": feature.get("geometry"), "properties": propriedades}


def adicionarCamadaReservatorios(mapa: folium.Map, geojson: dict) -> None:
    feicoes = [_prepararReservatorio(f) for f in geojson.get("features", [])]
    if not feicoes:
        return
    grupo = folium.FeatureGroup(name=rotuloLegenda(COR_RESERVATORIO, "Reservatórios Monitorados"), overlay=True)
    folium.GeoJson(
        {"type": "FeatureCollection", "features": feicoes},
        style_function=lambda _: {"fillColor": COR_RESERVATORIO, "color": "#000000", "weight": 1, "fillOpacity": 0.7},
        tooltip=folium.GeoJsonTooltip(
            fields=[c for c, _ in CAMPOS_RESERVATORIO], aliases=[a for _, a in CAMPOS_RESERVATORIO], sticky=True
        ),
    ).add_to(grupo)
    cluster = MarkerCluster().add_to(grupo)
    for feature in feicoes:
        try:
            centro = shape(feature["geometry"]).centroid
        except Exception:
            continue
        p = feature["properties"]
        tooltip = (
            f"<b>{p['nome']}</b><br><b>{p['proprietario']}</b><br><b>{p['gerencia']}</b><br>"
            f"<b>{p['reg_hidrog']}</b><br>Município: {p['nome_municipio_original']}<br>"
            f"Ano de Construção: {p['ano_constr']}<br>Rio/Riacho: {p['ri']}<br>"
            f"Barragem: {p['o_barrad']}<br>Capacidade: {p['capacid_m3']} m³"
        )
        folium.Marker(
            [centro.y, centro.x], tooltip=tooltip, icon=folium.Icon(prefix="fa", icon="tint", color="blue")
        ).add_to(cluster)
    grupo.add_to(mapa)


def renderizar() -> None:
    try:
        municipios = repositorio.carregarMunicipiosComReservatorio()
    except ErroApi:
        municipios = []

    col1, col2 = st.columns([7, 3])
    with col2:
        paragrafoInformativo(
            "Este mapa exibe os reservatórios monitorados no Ceará, permitindo filtrar "
            "por município e visualizar informações detalhadas como nome, capacidade, "
            "área, ano de construção e o rio associado.",
            estilo="padding-bottom: 0px",
        )
        cabecalhoFiltros()
        municipio = st.selectbox("Município", [TODOS] + municipios, index=0)
        try:
            reservatorios = repositorio.carregarReservatorios("todos" if municipio == TODOS else municipio)
        except ErroApi:
            mostrarErroDados()
            return
        estatisticas = calcularEstatisticas(reservatorios)
        paragrafoInformativo(
            "Inclui também camadas com limites municipais e assentamentos rurais "
            "para contexto geográfico,oferecendo uma visão integrada dos recursos hídricos.",
            estilo="padding-bottom: 0px",
        )
        st.metric("Reservatórios", estatisticas["total"])
        st.metric("Capacidade total (m³)", f"{estatisticas['capacidadeTotalM3']:.2f}".replace(".", ","))
        st.metric("Área total (ha)", f"{estatisticas['areaTotalHa']:.2f}".replace(".", ","))

    with col1:
        mapa = criarMapaBase()
        try:
            adicionarCamadaMunicipios(mapa, repositorio.carregarLimitesMunicipais())
            adicionarCamadasAssentamentos(mapa, repositorio.carregarAssentamentos("todos", TOLERANCIA_ASSENTAMENTOS))
        except ErroApi:
            st.warning("As camadas de contexto não puderam ser carregadas.")
        if reservatorios.get("features"):
            adicionarCamadaReservatorios(mapa, reservatorios)
        else:
            st.warning("Nenhum reservatório encontrado para esse filtro.")
        adicionarControles(mapa)
        renderizarMapa(mapa)
