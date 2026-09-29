# app.py
"""Ponto de entrada do dashboard: configuração da página, menu lateral e página ativa."""

import streamlit as st

st.set_page_config(
    page_title="Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from modules import navegacao  # noqa: E402
from modules.componentesUi import aplicarCss, tituloPagina  # noqa: E402

aplicarCss()
st.logo("./assets/Frame 18.png", size="large")

paginaAtual = navegacao.obterPaginaAtual()
navegacao.renderizarMenu(paginaAtual)
if paginaAtual.titulo:
    tituloPagina(paginaAtual.titulo)
paginaAtual.renderizar()
