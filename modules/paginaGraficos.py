# modules/paginaGraficos.py
"""Página Gráficos e Quadros: imóveis por categoria de tamanho em módulos fiscais.

As figuras são criadas com ``matplotlib.figure.Figure``, fora do pyplot, e
convertidas em PNG. O cache guarda o PNG a partir dos dados agregados, que são
pequenos, então nenhuma figura fica registrada na memória do processo.
"""

import io

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

from modules import config, repositorio
from modules.apiCliente import ErroApi
from modules.classificacao import contarPorCategoria, somarAreaPorCategoria
from modules.componentesUi import mostrarErroDados
from modules.privacidade import escaparHtml
from public.cores import CORES

ESCOPOS = ["Todo o Estado", "Municípios", "Regiões Administrativas"]
TOTAL_ESTIMADO_IMOVEIS = 312000
DPI_GRAFICOS = 150


def filtrarLotes(df: pd.DataFrame, escopo: str, entidade: str | None = None) -> pd.DataFrame:
    if escopo == "Todo o Estado":
        return df
    if escopo == "Municípios":
        return df[df["nome_municipio"] == entidade]
    if escopo == "Regiões Administrativas":
        return df[df["regiao_administrativa"] == entidade]
    raise ValueError(f"Escopo desconhecido: {escopo}")


def plotarBarras(resultados: dict, titulo: str, subtitulo: str) -> Figure:
    """Barras com a quantidade de imóveis por categoria e o total anotado em cada barra."""
    fig = Figure(figsize=(10, 10))
    ax = fig.subplots()
    barras = ax.bar(
        list(resultados.keys()),
        list(resultados.values()),
        color=[CORES[cat] for cat in resultados],
        edgecolor="black",
        alpha=0.85,
    )
    ax.set_title(f"{titulo}\n{subtitulo}", fontsize=16)
    ax.set_xlabel("Categoria", fontsize=14)
    ax.set_ylabel("Número de Propriedades", fontsize=14)
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.tick_params(axis="x", labelrotation=45, labelsize=12)
    for barra in barras:
        altura = barra.get_height()
        ax.annotate(
            f"{int(altura)}",
            xy=(barra.get_x() + barra.get_width() / 2, altura),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    fig.tight_layout()
    return fig


def plotarPizza(resultados: dict, titulo: str, subtitulo: str) -> Figure:
    """Pizza com a participação de cada categoria no número de imóveis."""
    fig = Figure(figsize=(10, 10))
    ax = fig.subplots()
    fatias, _ = ax.pie(
        list(resultados.values()), labels=None, startangle=90, colors=[CORES[cat] for cat in resultados]
    )
    ax.set_title(f"{titulo}\n{subtitulo}", fontsize=16)
    ax.axis("equal")
    total = sum(resultados.values())
    legendas = [f"{cat} ({valor / total * 100:.1f}%)" for cat, valor in resultados.items()]
    ax.legend(
        fatias, legendas, title="Tipos de Propriedade", loc="upper right",
        bbox_to_anchor=(1, 0, 0.5, 1), title_fontsize="15", fontsize=13,
    )
    fig.subplots_adjust(right=0.7)
    return fig


def plotarAreaPizza(areaPorCategoria: dict) -> Figure:
    """Pizza com a participação de cada categoria na área total."""
    areaTotal = sum(areaPorCategoria.values())
    fig = Figure(figsize=(8, 8))
    ax = fig.subplots()
    ax.set_title(f"Total de Área: {areaTotal:.2f} ha".replace(".", ","), fontsize=18)
    fatias, _, percentuais = ax.pie(
        list(areaPorCategoria.values()),
        labels=None,
        colors=[CORES[cat] for cat in areaPorCategoria],
        startangle=90,
        autopct="%1.1f%%",
        pctdistance=0.75,
        textprops={"fontsize": 12},
    )
    for texto in percentuais:
        texto.set_color("black")
        texto.set_fontweight("bold")
    legendas = [f"{cat} ({area / areaTotal * 100:.1f}%)" for cat, area in areaPorCategoria.items()]
    ax.legend(
        fatias, legendas, title="Tipos de Propriedade", loc="upper center",
        bbox_to_anchor=(1, 0, 0.5, 1), fontsize=14, title_fontsize=13,
    )
    fig.tight_layout()
    fig.subplots_adjust(right=0.7)
    return fig


def plotarSituacaoCadastro(totalCadastrados: int, totalEstimado: int = TOTAL_ESTIMADO_IMOVEIS) -> Figure:
    """Pizza de imóveis cadastrados e a cadastrar.

    Não está em uso: a aba "Gráfico de Geocadastro" aguarda decisão (D-2 do plano).
    """
    valores = {"Imóveis Cadastrados": totalCadastrados, "A Cadastrar": totalEstimado - totalCadastrados}
    cores = {"Imóveis Cadastrados": "#1f77b4", "A Cadastrar": "#ff7f0e"}
    fig = Figure(figsize=(8, 8))
    ax = fig.subplots()
    fatias, _, percentuais = ax.pie(
        list(valores.values()), labels=None, colors=[cores[c] for c in valores], startangle=90,
        autopct="%1.1f%%", pctdistance=0.75, textprops={"fontsize": 12},
    )
    for texto in percentuais:
        texto.set_color("white")
        texto.set_fontweight("bold")
        texto.set_fontsize(11)
    ax.set_title(
        f"Situação de Cadastro de Imóveis\nTotal Estimado: {totalEstimado:,} imóveis",
        fontsize=16, pad=20, fontweight="bold",
    )
    legendas = [f"{cat}\n{val:,.0f} imóveis ({val / totalEstimado * 100:.1f}%)" for cat, val in valores.items()]
    ax.legend(fatias, legendas, title="Situação do Cadastro", loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1), fontsize=12, title_fontsize=13)
    fig.tight_layout()
    fig.subplots_adjust(right=0.7)
    return fig


def figuraParaPng(fig: Figure) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI_GRAFICOS, bbox_inches="tight")
    return buffer.getvalue()


@st.cache_data(ttl=config.TTL_DADOS, show_spinner=False, max_entries=500)
def gerarGraficos(resultados: dict, areaPorCategoria: dict, titulo: str, subtitulo: str) -> tuple[bytes, bytes, bytes]:
    """PNG da pizza, das barras e da pizza de áreas, gerados a partir dos dados agregados."""
    return (
        figuraParaPng(plotarPizza(resultados, titulo, subtitulo)),
        figuraParaPng(plotarBarras(resultados, titulo, subtitulo)),
        figuraParaPng(plotarAreaPizza(areaPorCategoria)),
    )


def renderizar() -> None:
    try:
        dfClassificado = repositorio.carregarLotesClassificados()
    except ErroApi:
        mostrarErroDados()
        return

    col1, col2 = st.columns([6, 4])
    abaPizza, abaBarras = col1.tabs(["Gráfico de Pizza", "Gráfico de Barras"])
    col2.markdown("### Parâmetros de Busca:")
    colEscopo, colEntidade = col2.columns([1, 1])
    escopo = colEscopo.selectbox("Filtrar por:", ESCOPOS)
    entidade = ""
    if escopo != "Todo o Estado":
        coluna = "nome_municipio" if escopo == "Municípios" else "regiao_administrativa"
        entidade = colEntidade.selectbox(f"{escopo}:", sorted(dfClassificado[coluna].dropna().unique()))

    dfFiltrado = filtrarLotes(dfClassificado, escopo, entidade)
    resultados, total = contarPorCategoria(dfFiltrado)
    if not resultados:
        st.warning("Nenhum dado disponível para o filtro selecionado.")
        return

    pngPizza, pngBarras, pngArea = gerarGraficos(
        resultados, somarAreaPorCategoria(dfFiltrado), f"Propriedades - {escopo} - {entidade}", f"Total: {total}"
    )
    abaPizza.image(pngPizza, width="stretch")
    abaBarras.image(pngBarras, width="stretch")

    col2.markdown("### Classificação de Propriedades")
    col2.html(f'<p id="op-ent"><b>{escaparHtml(escopo)}</b> - {escaparHtml(entidade)} </p>')
    tabela = pd.DataFrame(list(resultados.items()), columns=["Categoria", "Quantidade"])
    tabela.loc[len(tabela)] = ["Total", total]
    col2.dataframe(tabela, width="stretch", hide_index=True)

    col2.markdown("#### Distribuição de Áreas por Tipo de Propriedade")
    col2.image(pngArea, width="stretch")
