# modules/componentesUi.py
"""Trechos de interface repetidos entre as páginas."""

from pathlib import Path

import streamlit as st

MENSAGEM_ERRO_DADOS = (
    "Não foi possível carregar os dados agora. Tente novamente em alguns minutos. "
    "Se o problema continuar, avise a equipe do Terra.Ce."
)


@st.cache_resource
def _lerCss() -> str:
    return Path("style.css").read_text(encoding="utf-8")


def aplicarCss() -> None:
    """Aplica o CSS do projeto. O arquivo é lido do disco uma vez por processo."""
    st.markdown(f"<style>{_lerCss()}</style>", unsafe_allow_html=True)


def tituloPagina(texto: str) -> None:
    st.markdown(f"## {texto}")


def paragrafoInformativo(texto: str, estilo: str = "") -> None:
    """Parágrafo com o ícone de informação. ``texto`` é HTML fixo do código, nunca dado da API."""
    atributoEstilo = f' style="{estilo}"' if estilo else ""
    st.html(f'<p class="paragrafo-com-icone"{atributoEstilo}><span class="icone-svg"></span> {texto}</p>')


def cabecalhoFiltros(titulo: str = "Filtros") -> None:
    st.markdown(f"### {titulo}")
    st.html("<span style='color: #000000 !important'>Do Estado do Ceará </span>")


def mostrarErroDados() -> None:
    st.error(MENSAGEM_ERRO_DADOS)
