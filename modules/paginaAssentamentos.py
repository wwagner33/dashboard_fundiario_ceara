# modules/paginaAssentamentos.py
"""Página Mapa de Assentamentos: assentamentos rurais estaduais e federais."""

import math

import streamlit as st

from modules import repositorio
from modules.apiCliente import ErroApi
from modules.camadasMapa import adicionarCamadaMunicipios, adicionarCamadasAssentamentos, adicionarControles, criarMapaBase, renderizarMapa
from modules.componentesUi import cabecalhoFiltros, mostrarErroDados, paragrafoInformativo
from modules.constantes import TOLERANCIA_ASSENTAMENTOS

TODOS = "Todos"
TIPOS = [TODOS, "Estadual", "Federal"]
ROTULOS = {"Estadual": "Estadual", "Federal": "Federal"}


def filtrarPorTipo(geojson: dict | None, tipo: str) -> dict:
    features = (geojson or {}).get("features", [])
    if tipo != TODOS:
        features = [
            f for f in features
            if str(f.get("properties", {}).get("tipo_assentamento") or "").lower() == tipo.lower()
        ]
    return {"type": "FeatureCollection", "features": features}


def calcularEstatisticas(geojson: dict | None) -> dict:
    """Total de assentamentos, área total e área média, ignorando áreas inválidas."""
    features = (geojson or {}).get("features", [])
    areas = []
    for feature in features:
        try:
            area = float(feature.get("properties", {}).get("area"))
        except (TypeError, ValueError):
            continue
        if not math.isnan(area):
            areas.append(area)
    return {
        "totalAssentamentos": len(features),
        "areaTotal": round(sum(areas), 2) if areas else 0,
        "areaMedia": round(sum(areas) / len(areas), 2) if areas else 0,
    }


def renderizar() -> None:
    try:
        municipios = repositorio.carregarMunicipiosComAssentamento()
    except ErroApi:
        municipios = []

    col1, col2 = st.columns([7, 3])
    with col2:
        paragrafoInformativo(
            "Este mapa exibe a localização geográfica dos assentamentos rurais no Ceará, "
            "diferenciando-os por tipo (Estadual ou Federal) e permitindo filtrar por município.",
            estilo="padding-bottom: 0px",
        )
        cabecalhoFiltros()
        municipio = st.selectbox("Selecione o município:", [TODOS] + municipios, index=0)
        tipo = st.selectbox("Selecione o tipo de assentamento:", TIPOS, index=0)
        paragrafoInformativo(
            "Cada assentamento contém informações detalhadas,como número de famílias, "
            "área e forma de obtenção,métricas gerais sobre quantidade e extensão das áreas.",
            estilo="padding-bottom: 0px",
        )
        st.markdown("### Informações")
        try:
            geojson = repositorio.carregarAssentamentos(
                "todos" if municipio == TODOS else municipio, TOLERANCIA_ASSENTAMENTOS
            )
        except ErroApi:
            mostrarErroDados()
            return
        filtrado = filtrarPorTipo(geojson, tipo)
        estatisticas = calcularEstatisticas(filtrado)
        st.metric("Total de assentamentos", estatisticas["totalAssentamentos"])
        st.metric("Área total (ha)", str(estatisticas["areaTotal"]).replace(".", ","))
        if municipio == TODOS and tipo == TODOS:
            st.metric("Área média (ha)", str(estatisticas["areaMedia"]).replace(".", ","))

    with col1:
        if not filtrado["features"]:
            st.warning("Nenhum dado disponível para os filtros selecionados.")
            return
        mapa = criarMapaBase()
        try:
            adicionarCamadaMunicipios(mapa, repositorio.carregarLimitesMunicipais(), comTooltip=False)
        except ErroApi:
            pass
        adicionarCamadasAssentamentos(mapa, filtrado, rotulos=ROTULOS, opacidade=0.7, comMarcadores=True)
        adicionarControles(mapa)
        renderizarMapa(mapa)
