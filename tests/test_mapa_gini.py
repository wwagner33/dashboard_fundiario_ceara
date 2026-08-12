"""Testes de lógica pura: modules/mapa_gini.py (cálculo do Índice de Gini)

Sem mocks de rede. Note que importar este módulo dispara a leitura de
st.secrets["JWT_SECRET"] (via modules.mapa_reservatorios) -- funciona porque
os testes rodam com cwd = dashboard_fundiario_ceara/.
"""
import math

import numpy as np
import pandas as pd
import pytest

from modules.mapa_gini import (
    calc_gini_df,
    contar_lotes,
    gini,
    normalizar_texto,
    processar_dataframes,
    style_fn,
)


# ---------------------------------------------------------------------------
# gini()
# ---------------------------------------------------------------------------

def test_gini_distribuicao_perfeitamente_igual_e_proxima_de_zero():
    valores = [10.0] * 20
    resultado = gini(valores)
    assert resultado == pytest.approx(0.0, abs=1e-9)


def test_gini_maxima_desigualdade_tende_a_um():
    # Um proprietário detém quase toda a área
    valores = [0.001] * 99 + [10_000.0]
    resultado = gini(valores)
    assert resultado > 0.9


def test_gini_array_vazio_retorna_nan():
    assert math.isnan(gini([]))


def test_gini_ignora_nan_e_negativos():
    com_ruido = [10.0, 10.0, float("nan"), -5.0, 10.0]
    sem_ruido = [10.0, 10.0, 10.0]
    assert gini(com_ruido) == pytest.approx(gini(sem_ruido))


def test_gini_soma_zero_retorna_nan():
    assert math.isnan(gini([0.0, 0.0]))


def test_gini_conhecido_duas_faixas():
    # 9 proprietários com 1 ha e 1 proprietário com 91 ha (total 100, n=10)
    valores = [1.0] * 9 + [91.0]
    resultado = gini(valores)
    # Gini = (2*sum(i*x_i))/(n*sum) - (n+1)/n calculado manualmente
    a = sorted(valores)
    n = len(a)
    total = sum(a)
    idx = list(range(1, n + 1))
    esperado = (2 * sum(i * x for i, x in zip(idx, a))) / (n * total) - (n + 1) / n
    assert resultado == pytest.approx(esperado)


# ---------------------------------------------------------------------------
# normalizar_texto()
# ---------------------------------------------------------------------------

def test_normalizar_texto_remove_acentos_e_minusculiza():
    assert normalizar_texto("José da Silva") == "jose da silva"


def test_normalizar_texto_preserva_nan():
    valor = float("nan")
    assert pd.isna(normalizar_texto(valor))


# ---------------------------------------------------------------------------
# processar_dataframes / contar_lotes / calc_gini_df
# ---------------------------------------------------------------------------

@pytest.fixture
def df_props():
    return pd.DataFrame({
        "nome_municipio": ["fortaleza"] * 5 + ["sobral"] * 3,
        "nome_municipio_original": ["Fortaleza"] * 5 + ["Sobral"] * 3,
        "regiao_administrativa": ["Norte"] * 5 + ["Sul"] * 3,
        "nome_proprietario": ["A", "A", "B", "C", "D", "E", "F", "G"],
        "area": [10.0, 5.0, 20.0, 8.0, 1000.0, 3.0, 4.0, 5.0],
    })


def test_processar_dataframes_agrupa_por_proprietario_e_municipio(df_props):
    out_iqr = pd.DataFrame(columns=df_props.columns)
    out_err = pd.DataFrame(columns=df_props.columns)

    df_with, df_no = processar_dataframes(df_props, out_iqr, out_err)

    # "A" tem dois lotes em fortaleza -> deve ser agregado (soma de área)
    linha_a = df_with[
        (df_with["nome_municipio"] == "fortaleza") & (df_with["nome_proprietario_normalizado"] == "a")
    ]
    assert len(linha_a) == 1
    assert linha_a["area"].iloc[0] == pytest.approx(15.0)
    # cnt_imoveis conta todos os lotes do município (não os agrupados)
    assert linha_a["cnt_imoveis"].iloc[0] == 5


def test_processar_dataframes_remove_outliers_do_df_no(df_props):
    # Marca o lote de 1000.0 ha como outlier
    out_err = df_props[df_props["area"] >= 500]
    out_iqr = pd.DataFrame(columns=df_props.columns)

    df_with, df_no = processar_dataframes(df_props, out_iqr, out_err)

    assert df_no["area"].max() < 500
    assert df_with["area"].max() >= 1000 or df_with.groupby("nome_municipio")["area"].sum().max() >= 1000


def test_contar_lotes_identifica_municipios_com_poucos_imoveis(df_props):
    out_iqr = pd.DataFrame(columns=df_props.columns)
    out_err = pd.DataFrame(columns=df_props.columns)
    df_with, df_no = processar_dataframes(df_props, out_iqr, out_err)

    _, _, warning_munis = contar_lotes(df_with, df_no)

    # Ambos municípios de teste têm poucos lotes (< 200)
    assert set(warning_munis) == {"fortaleza", "sobral"}


def test_calc_gini_df_produz_uma_linha_por_municipio(df_props):
    out_iqr = pd.DataFrame(columns=df_props.columns)
    out_err = pd.DataFrame(columns=df_props.columns)
    df_with, df_no = processar_dataframes(df_props, out_iqr, out_err)
    df_with, _, _ = contar_lotes(df_with, df_no)

    resultado = calc_gini_df(df_with)

    assert set(resultado["nome_municipio"]) == {"fortaleza", "sobral"}
    assert "gini_area" in resultado.columns
    assert "cnt_proprietarios" in resultado.columns


# ---------------------------------------------------------------------------
# style_fn() - faixas de cor do coroplético
# ---------------------------------------------------------------------------

def _feature(cnt_imoveis, gini_area):
    return {"properties": {"cnt_imoveis": cnt_imoveis, "gini_area": gini_area}}


def test_style_fn_municipio_com_poucos_imoveis_usa_cor_de_aviso():
    from public.cores import CORES_GINI
    result = style_fn(_feature(100, 0.5))
    assert result["fillColor"] == CORES_GINI[0]


def test_style_fn_sem_dados_usa_cinza():
    result = style_fn(_feature(300, float("nan")))
    assert result["fillColor"] == "#D3D3D3"


@pytest.mark.parametrize("valor_gini, faixa_idx", [
    (0.5, 1),
    (0.75, 2),
    (0.82, 3),
    (0.88, 4),
    (0.95, 5),
])
def test_style_fn_faixas_de_gini(valor_gini, faixa_idx):
    from public.cores import CORES_GINI
    result = style_fn(_feature(300, valor_gini))
    assert result["fillColor"] == CORES_GINI[faixa_idx]
