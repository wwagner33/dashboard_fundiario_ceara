"""Testes de lógica pura: modules/mapa_predominancia.py (agregação para o
mapa de categoria dominante por município)."""
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from modules.mapa_predominancia import preparar_dados

CATEGORIAS = [
    "Pequena Propriedade < 1 MF",
    "Pequena Propriedade",
    "Média Propriedade",
    "Grande Propriedade",
]


def _square(x0):
    return Polygon([(x0, 0), (x0 + 1, 0), (x0 + 1, 1), (x0, 1)])


@pytest.fixture
def muni_gdf():
    return gpd.GeoDataFrame(
        {"nome_municipio": ["fortaleza", "sobral", "iguatu"]},
        geometry=[_square(0), _square(2), _square(4)],
        crs="EPSG:4326",
    )


def test_preparar_dados_identifica_categoria_dominante(muni_gdf):
    df_ctx = pd.DataFrame({
        "nome_municipio": [
            "fortaleza", "fortaleza", "fortaleza",  # dominante: Pequena Propriedade
            "sobral",                                 # dominante: Grande Propriedade
        ],
        "categoria": [
            "Pequena Propriedade", "Pequena Propriedade", "Média Propriedade",
            "Grande Propriedade",
        ],
    })

    gdf_geo, df_tabular, debug_info = preparar_dados(df_ctx, muni_gdf, CATEGORIAS)

    linha_fortaleza = df_tabular[df_tabular["nome_municipio"] == "fortaleza"].iloc[0]
    assert linha_fortaleza["dominante"] == "Pequena Propriedade"
    assert linha_fortaleza["total"] == 3
    assert linha_fortaleza["prop_dom"] == pytest.approx(2 / 3)

    linha_sobral = df_tabular[df_tabular["nome_municipio"] == "sobral"].iloc[0]
    assert linha_sobral["dominante"] == "Grande Propriedade"


def test_preparar_dados_municipio_sem_registros_fica_marcado(muni_gdf):
    df_ctx = pd.DataFrame({
        "nome_municipio": ["fortaleza"],
        "categoria": ["Pequena Propriedade"],
    })

    gdf_geo, df_tabular, debug_info = preparar_dados(df_ctx, muni_gdf, CATEGORIAS)

    # iguatu não tem nenhum registro em df_ctx: não aparece em df_tabular
    # (que é derivado só de df_ctx), mas deve aparecer em gdf_geo (merge "left"
    # a partir de todos os municípios), já com os valores default aplicados.
    assert "iguatu" not in set(df_tabular["nome_municipio"])

    linha_iguatu = gdf_geo[gdf_geo["nome_municipio"] == "iguatu"].iloc[0]
    assert linha_iguatu["dominante"] == "Sem Registros"
    assert linha_iguatu["total"] == 0
    assert linha_iguatu["prop_dom"] == 0


def test_preparar_dados_mantem_todos_municipios_no_geodataframe(muni_gdf):
    df_ctx = pd.DataFrame({"nome_municipio": ["fortaleza"], "categoria": ["Pequena Propriedade"]})

    gdf_geo, df_tabular, debug_info = preparar_dados(df_ctx, muni_gdf, CATEGORIAS)

    # O merge é "left" a partir de muni_gdf, então nenhum município deve se perder
    assert len(gdf_geo) == len(muni_gdf) == 3
    assert set(gdf_geo["nome_municipio"]) == {"fortaleza", "sobral", "iguatu"}


def test_preparar_dados_debug_info_conta_municipios_com_e_sem_dados(muni_gdf):
    df_ctx = pd.DataFrame({
        "nome_municipio": ["fortaleza", "sobral"],
        "categoria": ["Pequena Propriedade", "Grande Propriedade"],
    })

    _, _, debug_info = preparar_dados(df_ctx, muni_gdf, CATEGORIAS)

    assert debug_info["municipios_recebidos"] == 3
    assert debug_info["municipios_com_dados"] == 2
    assert debug_info["municipios_sem_dados"] == 1
