"""Testes de modules/paginaConcentracao.py: Índice de Gini e clique no mapa."""
import math

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from modules import paginaConcentracao as pc
from public.cores import CORES_GINI


def test_giniDeDistribuicaoIgualEZero():
    assert pc.calcularGini([10.0] * 20) == pytest.approx(0.0, abs=1e-9)


def test_giniDeDesigualdadeMaximaTendeAUm():
    assert pc.calcularGini([0.001] * 99 + [10_000.0]) > 0.9


def test_giniVazioOuSomaZeroEhNaN():
    assert math.isnan(pc.calcularGini([]))
    assert math.isnan(pc.calcularGini([0.0, 0.0]))


def test_giniIgnoraNaNENegativos():
    assert pc.calcularGini([10.0, 10.0, float("nan"), -5.0, 10.0]) == pytest.approx(pc.calcularGini([10.0] * 3))


def test_giniConfereComAFormula():
    valores = sorted([1.0] * 9 + [91.0])
    n, total = len(valores), sum(valores)
    esperado = 2 * sum(i * x for i, x in enumerate(valores, start=1)) / (n * total) - (n + 1) / n
    assert pc.calcularGini(valores) == pytest.approx(esperado)


def test_normalizarNomesRemoveAcentoEPreservaAusentes():
    resultado = pc.normalizarNomes(pd.Series(["José da Silva", None, float("nan")]))
    assert resultado.iloc[0] == "jose da silva"
    assert resultado.iloc[1:].isna().all()


@pytest.fixture
def lotes():
    return pd.DataFrame({
        "nome_municipio": ["fortaleza"] * 5 + ["sobral"] * 3,
        "nome_municipio_original": ["Fortaleza"] * 5 + ["Sobral"] * 3,
        "regiao_administrativa": ["Norte"] * 5 + ["Sul"] * 3,
        "nome_proprietario": ["A", "á", "B", "C", "D", "E", "F", "G"],
        "area": [10.0, 5.0, 20.0, 8.0, 1000.0, 3.0, 4.0, 5.0],
    })


def test_baseAgrupaAreaPorProprietarioNormalizado(lotes):
    base = pc.prepararBaseGini(lotes)
    linha = base[(base["nome_municipio"] == "fortaleza") & (base["nome_proprietario_normalizado"] == "a")]
    assert linha["area"].iloc[0] == pytest.approx(15.0)
    assert linha["cnt_imoveis"].iloc[0] == 5


def test_giniPorMunicipioTemUmaLinhaPorMunicipio(lotes):
    tabela = pc.calcularGiniPorMunicipio(pc.prepararBaseGini(lotes))
    assert set(tabela["nome_municipio"]) == {"fortaleza", "sobral"}
    assert tabela.set_index("nome_municipio").loc["fortaleza", "cnt_proprietarios"] == 4


def test_municipiosComPoucosImoveis(lotes):
    tabela = pc.calcularGiniPorMunicipio(pc.prepararBaseGini(lotes))
    assert set(pc.municipiosComPoucosImoveis(tabela)) == {"fortaleza", "sobral"}


def _feicao(cnt, gini):
    return {"properties": {"cnt_imoveis": cnt, "gini_area": gini}}


def test_estiloDeMunicipioComPoucosImoveis():
    assert pc.estiloGini(_feicao(100, 0.5))["fillColor"] == CORES_GINI[0]


@pytest.mark.parametrize("gini", [None, float("nan")])
def test_estiloSemDados(gini):
    assert pc.estiloGini(_feicao(300, gini))["fillColor"] == pc.COR_SEM_DADOS


@pytest.mark.parametrize("gini, faixa", [(0.5, 1), (0.75, 2), (0.82, 3), (0.88, 4), (0.95, 5)])
def test_estiloPorFaixa(gini, faixa):
    assert pc.estiloGini(_feicao(300, gini))["fillColor"] == CORES_GINI[faixa]


@pytest.fixture
def tabelaGini():
    return pd.DataFrame({"nome_municipio": ["sao_goncalo_do_amarante"], "nome_municipio_original": ["São Gonçalo do Amarante"]})


def test_cliqueLeONomeDaFeicao(tabelaGini):
    # Regressão do bug B6: o nome vem das propriedades, não do texto do tooltip.
    dados = {"last_active_drawing": {"properties": {"nome_municipio": "sao_goncalo_do_amarante"}},
             "last_object_clicked": {"lat": -3.6, "lng": -38.9}}
    clique = pc.obterMunicipioClicado(dados, tabelaGini)
    assert clique["nome"] == "sao_goncalo_do_amarante"
    assert clique["identidade"] == "sao_goncalo_do_amarante|-3.6|-38.9"


def test_cliqueSemFeicaoUsaOTooltipEConverteONome(tabelaGini):
    dados = {"last_object_clicked_tooltip": "Município: \n São Gonçalo do Amarante \n Índice de Gini: \n 0,8"}
    assert pc.obterMunicipioClicado(dados, tabelaGini)["nome"] == "sao_goncalo_do_amarante"


@pytest.mark.parametrize("dados", [None, {}, {"last_object_clicked_tooltip": "texto sem nome"}])
def test_semCliqueReconhecido(dados, tabelaGini):
    assert pc.obterMunicipioClicado(dados, tabelaGini) is None


def test_mapaNaoExpoeNomesDeProprietarios(lotes):
    limites = gpd.GeoDataFrame(
        {"nome_municipio": ["fortaleza", "sobral"]},
        geometry=[Polygon([(-39, -4), (-38, -4), (-38, -3)]), Polygon([(-41, -4), (-40, -4), (-40, -3)])],
        crs="EPSG:4326",
    )
    lotes = lotes.assign(nome_proprietario=["Maria Joaquina"] * 8)
    geo, _, _ = pc._calcularTabelas.__wrapped__(1.0, 1, lotes, limites)
    html = pc.criarMapaGini(geo).get_root().render()
    assert "Maria Joaquina" not in html and "maria joaquina" not in html
    assert "fortaleza" in html
