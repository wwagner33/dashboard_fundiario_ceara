"""Testes de modules/paginaPredominancia.py: categoria dominante por município."""
import inspect

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from modules import paginaPredominancia as pp


def _quadrado(x0):
    return Polygon([(x0, 0), (x0 + 1, 0), (x0 + 1, 1), (x0, 1)])


@pytest.fixture
def limites():
    return gpd.GeoDataFrame(
        {"nome_municipio": ["fortaleza", "sobral", "iguatu"]},
        geometry=[_quadrado(-39), _quadrado(-40), _quadrado(-41)],
        crs="EPSG:4326",
    )


@pytest.fixture
def lotes():
    return pd.DataFrame({
        "nome_municipio": ["fortaleza", "fortaleza", "fortaleza", "sobral"],
        "categoria": ["Pequena Propriedade", "Pequena Propriedade", "Média Propriedade", "Grande Propriedade"],
    })


def test_identificaACategoriaDominante(lotes, limites):
    _, tabela = pp.prepararDados(lotes, limites)
    fortaleza = tabela.set_index("nome_municipio").loc["fortaleza"]
    assert fortaleza["dominante"] == "Pequena Propriedade"
    assert fortaleza["total"] == 3
    assert fortaleza["prop_dom"] == pytest.approx(2 / 3)


def test_municipioSemLotesEntraNaTabelaComZero(lotes, limites):
    # Regressão do bug B2: iguatu não tem lotes e precisa estar na tabela.
    gdf, tabela = pp.prepararDados(lotes, limites)
    iguatu = tabela.set_index("nome_municipio").loc["iguatu"]
    assert iguatu["total"] == 0
    assert iguatu["dominante"] == pp.SEM_REGISTROS
    assert set(gdf["nome_municipio"]) == {"fortaleza", "sobral", "iguatu"}


def test_tabelaDoMunicipioSemCadastroMostraZeros(lotes, limites):
    _, tabela = pp.prepararDados(lotes, limites)
    resultado = pp.tabelaDoMunicipio(tabela, "municipio_inexistente")
    assert resultado["Quantidade de Imóveis"].sum() == 0
    assert "Total" in resultado.index


def test_semNenhumLoteTodosOsMunicipiosFicamSemRegistros(limites):
    vazio = pd.DataFrame({"nome_municipio": [], "categoria": []})
    _, tabela = pp.prepararDados(vazio, limites)
    assert (tabela["dominante"] == pp.SEM_REGISTROS).all()


def test_modoPadraoEOMapaDePredominancia():
    # Regressão do bug B3.
    assert inspect.signature(pp.criarMapaPredominancia).parameters["modo"].default == pp.MODO_PREDOMINANTE


@pytest.mark.parametrize("modo", [pp.MODO_CALOR, pp.MODO_PREDOMINANTE])
def test_mapaRenderizaNosDoisModos(lotes, limites, modo):
    gdf, _ = pp.prepararDados(lotes, limites)
    geojson = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"nome_municipio": n}, "geometry": g.__geo_interface__}
        for n, g in zip(limites["nome_municipio"], limites.geometry, strict=True)
    ]}
    html = pp.criarMapaPredominancia(gdf, modo, "Pequena Propriedade", geojson).get_root().render()
    assert "Classificação dos Lotes" in html


def test_poligonosDosMunicipiosAparecemUmaVezNoModoPredominante(lotes, limites):
    gdf, _ = pp.prepararDados(lotes, limites)
    html = pp.criarMapaPredominancia(gdf, pp.MODO_PREDOMINANTE).get_root().render()
    assert html.count('"nome_municipio": "iguatu"') == 1
