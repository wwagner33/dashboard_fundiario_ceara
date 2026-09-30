"""Testes de modules/classificacao.py: faixas de módulo fiscal."""
import pandas as pd
import pytest

from modules.classificacao import (
    CATEGORIAS, SEM_CLASSIFICACAO, classificarPorModuloFiscal, contarPorCategoria,
    prepararLotesClassificados, somarAreaPorCategoria,
)


@pytest.mark.parametrize("area, esperado", [
    (4.99, "Pequena Propriedade < 1 MF"),
    (5.0, "Pequena Propriedade"),      # igual a 1 MF não é "< 1 MF"
    (20.0, "Pequena Propriedade"),     # igual a 4 MF
    (20.01, "Média Propriedade"),
    (75.0, "Média Propriedade"),       # igual a 15 MF
    (75.01, "Grande Propriedade"),
])
def test_fronteirasDasFaixas(area, esperado):
    assert classificarPorModuloFiscal([area], [5.0])[0] == esperado


def test_valorAusenteFicaSemClassificacao():
    assert classificarPorModuloFiscal([float("nan")], [5.0])[0] == SEM_CLASSIFICACAO


def test_prepararLotesDescartaSemAreaOuModulo():
    df = pd.DataFrame({"area": [1.0, None, 10.0], "modulo_fiscal": [5.0, 5.0, None]})
    resultado = prepararLotesClassificados(df)
    assert len(resultado) == 1
    assert resultado["categoria"].iloc[0] == "Pequena Propriedade < 1 MF"


def test_prepararLotesVazioDevolveColunaCategoria():
    resultado = prepararLotesClassificados(pd.DataFrame({"area": [], "modulo_fiscal": []}))
    assert "categoria" in resultado.columns


def test_contarPorCategoriaSegueAOrdemDasCategorias():
    df = pd.DataFrame({"categoria": ["Grande Propriedade", "Pequena Propriedade", "Grande Propriedade"]})
    contagem, total = contarPorCategoria(df)
    assert list(contagem) == ["Pequena Propriedade", "Grande Propriedade"]
    assert contagem["Grande Propriedade"] == 2
    assert total == 3


def test_somarAreaPorCategoria():
    df = pd.DataFrame({"categoria": [CATEGORIAS[0], CATEGORIAS[0], CATEGORIAS[3]], "area": [1.0, 2.0, 100.0]})
    assert somarAreaPorCategoria(df) == {CATEGORIAS[0]: 3.0, CATEGORIAS[3]: 100.0}
