"""Testes de modules/paginaGraficos.py: filtros e geração dos gráficos."""
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from modules import paginaGraficos
from modules.classificacao import contarPorCategoria, prepararLotesClassificados, somarAreaPorCategoria


@pytest.fixture
def dfClassificado():
    return prepararLotesClassificados(pd.DataFrame({
        "nome_municipio": ["fortaleza", "fortaleza", "sobral", "sobral"],
        "regiao_administrativa": ["Norte", "Norte", "Sul", "Sul"],
        "modulo_fiscal": [5.0] * 4,
        "area": [0.5, 10.0, 50.0, 200.0],
    }))


def test_filtrarTodoOEstado(dfClassificado):
    assert len(paginaGraficos.filtrarLotes(dfClassificado, "Todo o Estado")) == 4


def test_filtrarPorMunicipio(dfClassificado):
    assert set(paginaGraficos.filtrarLotes(dfClassificado, "Municípios", "sobral")["nome_municipio"]) == {"sobral"}


def test_filtrarPorRegiao(dfClassificado):
    assert len(paginaGraficos.filtrarLotes(dfClassificado, "Regiões Administrativas", "Norte")) == 2


def test_escopoDesconhecidoGeraErro(dfClassificado):
    with pytest.raises(ValueError):
        paginaGraficos.filtrarLotes(dfClassificado, "Outro")


def test_funcoesDePlotagemDevolvemFigure(dfClassificado):
    resultados, total = contarPorCategoria(dfClassificado)
    assert isinstance(paginaGraficos.plotarBarras(resultados, "T", f"Total: {total}"), Figure)
    assert isinstance(paginaGraficos.plotarPizza(resultados, "T", f"Total: {total}"), Figure)
    assert isinstance(paginaGraficos.plotarAreaPizza(somarAreaPorCategoria(dfClassificado)), Figure)
    assert isinstance(paginaGraficos.plotarSituacaoCadastro(1000), Figure)


def test_gerarGraficosDevolvePngSemAcumularFigurasNoPyplot(dfClassificado):
    # Regressão de D7: as figuras não podem ficar registradas no pyplot.
    abertasAntes = len(plt.get_fignums())
    resultados, total = contarPorCategoria(dfClassificado)
    for indice in range(3):
        pngs = paginaGraficos.gerarGraficos(resultados, somarAreaPorCategoria(dfClassificado), f"T{indice}", "S")
        assert all(png.startswith(b"\x89PNG") for png in pngs)
    assert len(plt.get_fignums()) == abertasAntes
