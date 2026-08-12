"""Testes de lógica pura: modules/grafico_interativo.py

Sem mocks de rede -- essas funções operam apenas sobre DataFrames em memória.
"""
import matplotlib
matplotlib.use("Agg")  # evita necessidade de display gráfico ao rodar os testes

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from modules.grafico_interativo import (
    classificar_propriedades,
    filtrar_dados,
    plot_area_pizza,
    plot_barras,
    plot_pizza,
)


@pytest.fixture
def df_class():
    return pd.DataFrame({
        "nome_municipio": ["fortaleza", "fortaleza", "sobral", "sobral"],
        "regiao_administrativa": ["Norte", "Norte", "Sul", "Sul"],
        "modulo_fiscal": [5.0, 5.0, 5.0, 5.0],
        "area": [0.5, 10.0, 50.0, 200.0],  # cobre as 4 categorias
    })


# ---------------------------------------------------------------------------
# filtrar_dados
# ---------------------------------------------------------------------------

def test_filtrar_dados_todo_estado_retorna_tudo(df_class):
    result = filtrar_dados(df_class, "Todo o Estado")
    assert len(result) == 4


def test_filtrar_dados_por_municipio(df_class):
    result = filtrar_dados(df_class, "Municípios", "fortaleza")
    assert len(result) == 2
    assert set(result["nome_municipio"]) == {"fortaleza"}


def test_filtrar_dados_por_regiao_administrativa(df_class):
    result = filtrar_dados(df_class, "Regiões Administrativas", "Sul")
    assert len(result) == 2
    assert set(result["regiao_administrativa"]) == {"Sul"}


def test_filtrar_dados_escopo_desconhecido_lanca_erro(df_class):
    with pytest.raises(ValueError):
        filtrar_dados(df_class, "Escopo Inexistente")


# ---------------------------------------------------------------------------
# classificar_propriedades
# ---------------------------------------------------------------------------

def test_classificar_propriedades_cobre_as_quatro_categorias(df_class):
    counts, total = classificar_propriedades(df_class)
    assert total == 4
    assert counts["Pequena Propriedade < 1 MF"] == 1
    assert counts["Pequena Propriedade"] == 1
    assert counts["Média Propriedade"] == 1
    assert counts["Grande Propriedade"] == 1


def test_classificar_propriedades_limites_exatos():
    # area == modulo_fiscal -> NÃO é "< 1 MF" (a condição é estritamente <)
    df = pd.DataFrame({"modulo_fiscal": [5.0], "area": [5.0]})
    counts, total = classificar_propriedades(df)
    assert counts.get("Pequena Propriedade") == 1
    assert total == 1


def test_classificar_propriedades_area_igual_a_4mf_e_pequena():
    df = pd.DataFrame({"modulo_fiscal": [5.0], "area": [20.0]})  # == 4*MF
    counts, _ = classificar_propriedades(df)
    assert counts.get("Pequena Propriedade") == 1


def test_classificar_propriedades_area_igual_a_15mf_e_media():
    df = pd.DataFrame({"modulo_fiscal": [5.0], "area": [75.0]})  # == 15*MF
    counts, _ = classificar_propriedades(df)
    assert counts.get("Média Propriedade") == 1


# ---------------------------------------------------------------------------
# Funções de plot (fumaça: garantem que não lançam exceção e retornam Figure)
# ---------------------------------------------------------------------------

def test_plot_barras_retorna_figure(df_class):
    resultados, total = classificar_propriedades(df_class)
    fig = plot_barras(resultados, "Título", f"Total: {total}")
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_plot_pizza_retorna_figure(df_class):
    resultados, total = classificar_propriedades(df_class)
    fig = plot_pizza(resultados, "Título", f"Total: {total}")
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_plot_area_pizza_retorna_figure(df_class):
    fig = plot_area_pizza(df_class, "Título")
    assert isinstance(fig, plt.Figure)
    plt.close(fig)
