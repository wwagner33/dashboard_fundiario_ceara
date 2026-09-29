# modules/paginaEscolasCampo.py
"""Página Mapa Escolas do Campo: escolas em assentamentos rurais, por CREDE."""

import folium
import streamlit as st
from folium.plugins import MarkerCluster

from modules import repositorio
from modules.apiCliente import ErroApi
from modules.camadasMapa import adicionarCamadaMunicipios, adicionarCamadasAssentamentos, adicionarControles, criarMapaBase, renderizarMapa, rotuloLegenda
from modules.componentesUi import cabecalhoFiltros, paragrafoInformativo
from modules.constantes import COR_ESCOLA, TOLERANCIA_ASSENTAMENTOS
from modules.privacidade import escaparHtml

TODOS = "Todos"

# nome_municipio segue o formato normalizado do miniserver (minúsculas, sem
# acento, espaço vira "_"); nome_municipio_original é o nome exibido.
ESCOLAS_DO_CAMPO = [
    {"crede": 2, "nome_municipio": "itapipoca", "nome_municipio_original": "Itapipoca", "assentamento": "Maceió",
     "nome_escola": "EEM Maria Nazaré de Sousa", "latitude": -3.129879627387401, "longitude": -39.52221661844289},
    {"crede": 3, "nome_municipio": "itarema", "nome_municipio_original": "Itarema", "assentamento": "Lagoa do Mineiro",
     "nome_escola": "EEM Francisco Araújo Barros", "latitude": -3.025238577636784, "longitude": -39.753315518444005},
    {"crede": 6, "nome_municipio": "santana_do_acarau", "nome_municipio_original": "Santana do Acaraú",
     "assentamento": "Conceição Bonfim", "nome_escola": "EEM José Fideles de Moura",
     "latitude": -3.386111233883421, "longitude": -40.28083861844071},
    {"crede": 7, "nome_municipio": "caninde", "nome_municipio_original": "Canindé", "assentamento": "Santana da Cal",
     "nome_escola": "EEM Filha da Luta Patativa do Assaré", "latitude": -4.375812781017249, "longitude": -39.45617268959514},
    {"crede": 7, "nome_municipio": "caninde", "nome_municipio_original": "Canindé", "assentamento": "Logradouro",
     "nome_escola": "EEM Antônio Tavares Alves", "latitude": -4.490990998155495, "longitude": -39.2107603049365},
    {"crede": 7, "nome_municipio": "caninde", "nome_municipio_original": "Canindé", "assentamento": "Conceição Salitre",
     "nome_escola": "EEM Javan Rodrigues de Sousa", "latitude": -4.214808199746922, "longitude": -39.7451775049393},
    {"crede": 8, "nome_municipio": "ocara", "nome_municipio_original": "Ocara", "assentamento": "Antônio Conselheiro",
     "nome_escola": "EEM Francisca Pinto dos Santos", "latitude": -4.58715153922025, "longitude": -38.61961616445614},
    {"crede": 11, "nome_municipio": "jaguaretama", "nome_municipio_original": "Jaguaretama", "assentamento": "Pedra e Cal",
     "nome_escola": "EEM Pe. José Augusto Régis Alves", "latitude": -5.468583905528393, "longitude": -38.75458134675905},
    {"crede": 12, "nome_municipio": "quixeramobim", "nome_municipio_original": "Quixeramobim", "assentamento": "Canaã",
     "nome_escola": "EEM Irmã Tereza Cristina", "latitude": -5.367998686093881, "longitude": -39.319097133761986},
    {"crede": 12, "nome_municipio": "madalena", "nome_municipio_original": "Madalena", "assentamento": "25 de Maio",
     "nome_escola": "EEM João dos Santos Oliveira", "latitude": -5.027589544256683, "longitude": -39.531745949108526},
    # Coordenada a conferir: o ponto cai em Fortaleza, não em Monsenhor Tabosa.
    {"crede": 13, "nome_municipio": "monsenhor_tabosa", "nome_municipio_original": "Monsenhor Tabosa",
     "assentamento": "Santana", "nome_escola": "EEM Florestan Fernandes",
     "latitude": -3.750725526452395, "longitude": -38.55615224542324},
    {"crede": 13, "nome_municipio": "ipueiras", "nome_municipio_original": "Ipueiras", "assentamento": "Distrito de Balseiros",
     "nome_escola": "EFA Padre Elfésio dos Santos", "latitude": -4.680048368725458, "longitude": -40.80273330493446},
    {"crede": 14, "nome_municipio": "mombaca", "nome_municipio_original": "Mombaça", "assentamento": "Salão Mombaça",
     "nome_escola": "EEM Paulo Freire", "latitude": -5.699846996424161, "longitude": -39.93511134725098},
]
NOMES_MUNICIPIOS = {e["nome_municipio"]: e["nome_municipio_original"] for e in ESCOLAS_DO_CAMPO}


def listarMunicipiosComEscolas() -> list[str]:
    """Chaves dos municípios com escola, em ordem alfabética do nome exibido."""
    return sorted(NOMES_MUNICIPIOS, key=lambda chave: NOMES_MUNICIPIOS[chave])


def filtrarEscolas(municipio: str) -> list[dict]:
    if municipio == TODOS:
        return ESCOLAS_DO_CAMPO
    return [e for e in ESCOLAS_DO_CAMPO if e["nome_municipio"] == municipio]


def calcularEstatisticas(escolas: list[dict]) -> dict:
    porCrede: dict[int, int] = {}
    for escola in escolas:
        porCrede[escola["crede"]] = porCrede.get(escola["crede"], 0) + 1
    return {"total": len(escolas), "porCrede": porCrede}


def adicionarCamadaEscolas(mapa: folium.Map, escolas: list[dict]) -> None:
    if not escolas:
        return
    grupo = folium.FeatureGroup(name=rotuloLegenda(COR_ESCOLA, "Escolas do Campo"), overlay=True)
    cluster = MarkerCluster().add_to(grupo)
    for escola in escolas:
        texto = (
            f"<b>CREDE: {escola['crede']}</b><br>"
            f"<b>Município: {escaparHtml(escola['nome_municipio_original'])}</b><br>"
            f"<b>Assentamento: {escaparHtml(escola['assentamento'])}</b><br>"
            f"<b>Escola: {escaparHtml(escola['nome_escola'])}</b>"
        )
        folium.Marker(
            [escola["latitude"], escola["longitude"]],
            tooltip=texto,
            popup=folium.Popup(texto, max_width=300),
            icon=folium.Icon(prefix="fa", icon="school", color="red"),
        ).add_to(cluster)
    grupo.add_to(mapa)


def renderizar() -> None:
    col1, col2 = st.columns([7, 3])
    with col2:
        paragrafoInformativo(
            "Este mapa exibe as escolas do campo no Ceará, permitindo filtrar "
            "por município e visualizar informações detalhadas como CREDE, "
            "assentamento e nome da escola.",
            estilo="padding-bottom: 0px",
        )
        cabecalhoFiltros()
        municipio = st.selectbox(
            "Município", [TODOS] + listarMunicipiosComEscolas(), index=0,
            format_func=lambda chave: NOMES_MUNICIPIOS.get(chave, chave),
        )
        escolas = filtrarEscolas(municipio)
        estatisticas = calcularEstatisticas(escolas)
        paragrafoInformativo(
            "Inclui também camadas com limites municipais e assentamentos rurais "
            "para contexto geográfico, oferecendo uma visão integrada da educação no campo.",
            estilo="padding-bottom: 0px",
        )
        st.metric("Escolas do Campo", estatisticas["total"])
        st.markdown("**Distribuição por CREDE:**")
        for crede, quantidade in estatisticas["porCrede"].items():
            st.markdown(f"- CREDE {crede}: {quantidade} escola(s)")

    with col1:
        mapa = criarMapaBase()
        try:
            adicionarCamadaMunicipios(mapa, repositorio.carregarLimitesMunicipais())
            adicionarCamadasAssentamentos(mapa, repositorio.carregarAssentamentos("todos", TOLERANCIA_ASSENTAMENTOS))
        except ErroApi:
            st.warning("As camadas de contexto não puderam ser carregadas.")
        adicionarCamadaEscolas(mapa, escolas)
        adicionarControles(mapa)
        renderizarMapa(mapa)
