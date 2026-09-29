# modules/paginaConcentracao.py
"""Página Mapa de Concentração Fundiária: Índice de Gini da área por proprietário.

O Gini de cada município considera a soma das áreas de cada proprietário no
município. O Gini estadual soma as áreas de cada proprietário no estado todo.
Os nomes dos proprietários só são usados para agrupar; nunca são exibidos.
"""

import html

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
from folium.features import GeoJsonTooltip
from folium.plugins import Fullscreen, MiniMap

from modules import config, repositorio
from modules.apiCliente import ErroApi
from modules.camadasMapa import criarMapaBase, renderizarMapa
from modules.componentesUi import mostrarErroDados, paragrafoInformativo
from modules.constantes import CRS_GEOGRAFICO, CRS_METRICO
from modules.privacidade import escaparColunasTexto, escaparHtml
from public.cores import CORES_GINI

LIMITE_MINIMO_IMOVEIS = 200
COR_SEM_DADOS = "#D3D3D3"
TODAS_REGIOES = "[TODAS]"
CHAVE_CLIQUE_DESCARTADO = "giniCliqueDescartado"
OBJETOS_RETORNADOS = ["last_active_drawing", "last_object_clicked", "last_object_clicked_tooltip"]


def calcularGini(valores) -> float:
    """Índice de Gini: (2 * Σ(i * x_i)) / (n * Σx_i) - (n + 1) / n.

    Ignora NaN, zeros e negativos. Devolve NaN para amostra vazia ou soma zero.
    """
    a = np.array(valores, dtype=float)
    a = np.sort(a[~np.isnan(a) & (a > 0)])
    n = a.size
    if n == 0 or a.sum() == 0:
        return float("nan")
    indices = np.arange(1, n + 1)
    return float((2 * (indices * a).sum()) / (n * a.sum()) - (n + 1) / n)


def normalizarNomes(serie: pd.Series) -> pd.Series:
    """Remove acentos e passa para minúsculas, preservando valores ausentes."""
    return (
        serie.astype(object).where(serie.notna())
        .str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii").str.lower()
    )


def prepararBaseGini(dfLotes: pd.DataFrame) -> pd.DataFrame:
    """Soma a área de cada proprietário por município e anexa o total de imóveis do município."""
    df = dfLotes[["nome_municipio", "nome_municipio_original", "regiao_administrativa", "nome_proprietario", "area"]].copy()
    df["nome_proprietario_normalizado"] = normalizarNomes(df["nome_proprietario"])
    contagem = df.groupby("nome_municipio").size().rename("cnt_imoveis").reset_index()
    agrupado = (
        df.groupby(["nome_municipio", "nome_proprietario_normalizado"])
        .agg(
            area=("area", "sum"),
            nome_municipio_original=("nome_municipio_original", "first"),
            regiao_administrativa=("regiao_administrativa", "first"),
        )
        .reset_index()
    )
    return agrupado.merge(contagem, on="nome_municipio", how="left")


def calcularGiniPorMunicipio(dfAgrupado: pd.DataFrame) -> pd.DataFrame:
    return (
        dfAgrupado.groupby("nome_municipio")
        .agg(
            nome_municipio_original=("nome_municipio_original", "first"),
            regiao_administrativa=("regiao_administrativa", "first"),
            cnt_imoveis=("cnt_imoveis", "first"),
            cnt_proprietarios=("nome_proprietario_normalizado", "nunique"),
            gini_area=("area", calcularGini),
        )
        .reset_index()
    )


def calcularGiniEstadual(dfAgrupado: pd.DataFrame) -> float:
    return calcularGini(dfAgrupado.groupby("nome_proprietario_normalizado")["area"].sum().values)


def municipiosComPoucosImoveis(giniPorMunicipio: pd.DataFrame) -> list[str]:
    """Municípios abaixo do mínimo de imóveis para um Gini confiável."""
    return giniPorMunicipio.loc[giniPorMunicipio["cnt_imoveis"] < LIMITE_MINIMO_IMOVEIS, "nome_municipio"].tolist()


@st.cache_resource(ttl=config.TTL_DADOS, show_spinner="Calculando o Índice de Gini...", max_entries=2)
def _calcularTabelas(versao: float, idLimites: int, _lotes: pd.DataFrame, _limites: gpd.GeoDataFrame):
    base = prepararBaseGini(_lotes)
    giniPorMunicipio = calcularGiniPorMunicipio(base)
    geo = _limites[["nome_municipio", "geometry"]].merge(giniPorMunicipio, on="nome_municipio", how="left")
    geo = gpd.GeoDataFrame(geo, geometry="geometry", crs=_limites.crs)
    return geo, giniPorMunicipio, calcularGiniEstadual(base)


def gerarGraficoCircular(valor: float, tamanho: int = 100) -> str:
    if pd.isna(valor):
        return "<div>Sem dados</div>"
    valorAbsoluto = f"{valor:.4f}".replace(".", ",")
    return f"""
    <style>
    .grafico {{
        --porcentagem: {valor:.2f};
        --tamanho: {tamanho}px;
        width: var(--tamanho);
        height: var(--tamanho);
        border-radius: 50%;
        background: conic-gradient(
            {CORES_GINI[2]} 0%,
            #f5e1df calc(var(--porcentagem) * 100%),
            #fcf1f0 0%
        );
        display: grid; place-items: center; margin: 10px auto;
    }}
    .grafico::before {{
        content: "{valorAbsoluto}";
        display: grid; place-items: center;
        width: 70%; height: 70%; background: white; border-radius: 50%;
        color: #0c0906; font-size: {tamanho * 0.15}px;
    }}
    </style>
    <div class="grafico" data-value="{valor:.0%}"></div>
    <p style='text-align:center;color:black; padding-bottom:0px; margin-right: auto;'>Percentual:</br> {valor:.2%}     </p>
    """


def estiloGini(feature: dict) -> dict:
    propriedades = feature["properties"]
    quantidade = propriedades.get("cnt_imoveis")
    valor = propriedades.get("gini_area")
    if quantidade and quantidade < LIMITE_MINIMO_IMOVEIS:
        cor = CORES_GINI[0]
    elif valor is None or pd.isna(valor):
        cor = COR_SEM_DADOS
    elif valor <= 0.700:
        cor = CORES_GINI[1]
    elif valor <= 0.800:
        cor = CORES_GINI[2]
    elif valor <= 0.850:
        cor = CORES_GINI[3]
    elif valor <= 0.900:
        cor = CORES_GINI[4]
    else:
        cor = CORES_GINI[5]
    return {"fillColor": cor, "color": "black", "weight": 0.5, "fillOpacity": 0.8}


_LEGENDA = f"""
<div style='position:fixed;top:10px;right:10px;background:white;padding:10px;border:1px solid grey;font-size:14px;z-index:9999;'>
<b>Intervalos de Gini</b><br>
<i style='background:{CORES_GINI[0]};width:12px;height:12px;float:left;margin-right:4px'></i> &lt;200 imóveis<br>
<i style='background:{CORES_GINI[1]};width:12px;height:12px;float:left;margin-right:4px'></i>≤0.700<br>
<i style='background:{CORES_GINI[2]};width:12px;height:12px;float:left;margin-right:4px'></i>0.701–0.800<br>
<i style='background:{CORES_GINI[3]};width:12px;height:12px;float:left;margin-right:4px'></i>0.801–0.850<br>
<i style='background:{CORES_GINI[4]};width:12px;height:12px;float:left;margin-right:4px'></i>0.851–0.900<br>
<i style='background:{CORES_GINI[5]};width:12px;height:12px;float:left;margin-right:4px'></i>&gt;0.900<br>
<i style='background:{COR_SEM_DADOS};width:12px;height:12px;float:left;margin-right:4px'></i>Sem dados
</div>"""


def criarMapaGini(geo: gpd.GeoDataFrame) -> folium.Map:
    """Coroplético do Gini com o nome de cada município no centróide."""
    mapa = criarMapaBase(centro=[-5.2, -39.5], zoom=8)
    colunas = ["nome_municipio", "nome_municipio_original", "gini_area", "cnt_imoveis", "cnt_proprietarios", "geometry"]
    dados = escaparColunasTexto(geo[colunas], ["nome_municipio", "nome_municipio_original"])
    folium.GeoJson(
        dados,
        style_function=estiloGini,
        tooltip=GeoJsonTooltip(
            fields=["nome_municipio_original", "gini_area", "cnt_imoveis", "cnt_proprietarios"],
            aliases=["Município: ", "Índice de Gini: ", "Imóveis: ", "Proprietários: "],
            localize=True,
            sticky=True,
        ),
        name="gini_map",
    ).add_to(mapa)

    validos = geo[geo.geometry.notna() & ~geo.geometry.is_empty]
    centros = validos.geometry.to_crs(CRS_METRICO).centroid.to_crs(CRS_GEOGRAFICO)
    for nome, ponto in zip(validos["nome_municipio"], centros, strict=True):
        folium.Marker(
            [ponto.y, ponto.x],
            icon=folium.DivIcon(
                html=f"<div style='font-size:6pt;font-weight:bold;color:black;text-shadow:0 0 4px white;'>{escaparHtml(nome)}</div>"
            ),
        ).add_to(mapa)

    mapa.get_root().html.add_child(folium.Element(_LEGENDA))
    MiniMap(toggle_display=True).add_to(mapa)
    Fullscreen().add_to(mapa)
    return mapa


def obterMunicipioClicado(dadosMapa: dict | None, giniPorMunicipio: pd.DataFrame) -> dict | None:
    """Município clicado no mapa, a partir das propriedades da feição.

    Se o componente não devolver a feição, usa o nome exibido no tooltip e o
    converte para o nome normalizado. Devolve ``None`` sem clique reconhecido.
    """
    if not dadosMapa:
        return None
    nome = ((dadosMapa.get("last_active_drawing") or {}).get("properties") or {}).get("nome_municipio")
    if nome:
        nome = html.unescape(str(nome))
    else:
        texto = dadosMapa.get("last_object_clicked_tooltip") or ""
        linhas = [linha.strip() for linha in texto.split("\n") if linha.strip()]
        if len(linhas) < 2:
            return None
        original = html.unescape(linhas[1])
        encontrados = giniPorMunicipio.loc[giniPorMunicipio["nome_municipio_original"] == original, "nome_municipio"]
        if encontrados.empty:
            return None
        nome = encontrados.iloc[0]
    clique = dadosMapa.get("last_object_clicked") or {}
    return {"nome": nome, "identidade": f"{nome}|{clique.get('lat')}|{clique.get('lng')}"}


def _descartarClique(identidade: str) -> None:
    st.session_state[CHAVE_CLIQUE_DESCARTADO] = identidade


@st.fragment
def _tabelaPorRegiao(giniPorMunicipio: pd.DataFrame) -> None:
    """Tabela por região. Roda como fragmento: trocar a região não reconstrói o mapa."""
    regioes = sorted(giniPorMunicipio["regiao_administrativa"].dropna().unique().tolist())
    regiao = st.selectbox("Filtrar por Região:", options=[TODAS_REGIOES] + regioes, index=0, key="giniRegiao")
    tabela = giniPorMunicipio if regiao == TODAS_REGIOES else giniPorMunicipio[giniPorMunicipio["regiao_administrativa"] == regiao]
    st.dataframe(
        tabela[["regiao_administrativa", "nome_municipio_original", "cnt_imoveis", "cnt_proprietarios", "gini_area"]]
        .rename(columns={
            "regiao_administrativa": "Região",
            "nome_municipio_original": "Município",
            "gini_area": "Gini",
            "cnt_imoveis": "Imóveis",
            "cnt_proprietarios": "Proprietários",
        })
        .sort_values("Município", ascending=True),
        width="stretch",
        hide_index=True,
        height=600,
    )


def renderizar() -> None:
    try:
        lotes = repositorio.carregarLotes()
        limites = repositorio.carregarLimitesMunicipaisGdf()
    except ErroApi:
        mostrarErroDados()
        return
    geo, giniPorMunicipio, giniEstadual = _calcularTabelas(repositorio.versaoDados(lotes), id(limites), lotes, limites)

    col1, col2 = st.columns([10, 3])
    with col1:
        dadosMapa = renderizarMapa(criarMapaGini(geo), altura=600, retornar=OBJETOS_RETORNADOS, chave="mapaGini")

    with col2:
        paragrafoInformativo(
            "Este mapa apresenta o Índice de Gini da distribuição fundiária por município no Ceará, "
            "permitindo identificar o grau de concentração de terras. "
            "Inclui também um indicador geral do estado. </br>"
            "As áreas em amarelo são regiões onde o número de imóveis é inferior a 200, portanto, "
            "abaixo do número mínimo de imóveis necessário para cálculo correto do Gini Fundiário. </br>"
            "Os municípios em branco, no mapa, são correspondentes às áreas áreas rurais ainda não regularizadas.",
            estilo="font-size: 14px !important;",
        )
        st.markdown("### Índice de Gini")
        st.html("<span style='color: #000000 !important'>Do Estado do Ceará </span>")

        clique = obterMunicipioClicado(dadosMapa, giniPorMunicipio)
        linha = pd.DataFrame()
        if clique and clique["identidade"] != st.session_state.get(CHAVE_CLIQUE_DESCARTADO):
            linha = giniPorMunicipio[giniPorMunicipio["nome_municipio"] == clique["nome"]]
        if not linha.empty and pd.notna(linha["gini_area"].iloc[0]):
            st.markdown(
                f"<p style='text-align: center; color:black;'>{escaparHtml(str(linha['nome_municipio_original'].iloc[0]))}</p>",
                unsafe_allow_html=True,
            )
            st.markdown(gerarGraficoCircular(float(linha["gini_area"].iloc[0]), 150), unsafe_allow_html=True)
            st.button(
                "Mostrar Gini Estadual Completo", key="mostrarGiniEstadual", width="stretch",
                on_click=_descartarClique, args=(clique["identidade"],),
            )
        else:
            st.markdown(gerarGraficoCircular(giniEstadual, 180), unsafe_allow_html=True)

        paragrafoInformativo(
            "As cores indicam faixas de desigualdade, e o usuário pode clicar "
            "sobre um município para visualizar seu valor específico em destaque, "
            "além de consultar rankings por região administrativa.",
            estilo="font-size: 16px !important;",
        )
        st.subheader("Gini por Região Administrativa")
        _tabelaPorRegiao(giniPorMunicipio)
