"""Testes de modules/mapa_assentamento.py: formatação, estatísticas e
chamadas HTTP (mockadas) para a API de assentamentos."""
import math

import pytest

from modules import mapa_assentamento as ma
from tests.conftest import SAMPLE_ASSENTAMENTOS_GEOJSON


# ---------------------------------------------------------------------------
# formatar_valor (lógica pura)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor, esperado", [
    (None, "Não Disponível"),
    (float("nan"), "Não Disponível"),
    ("", "Não Disponível"),
    ("   ", "Não Disponível"),
    ("nan", "Não Disponível"),
    ("None", "Não Disponível"),
    ("null", "Não Disponível"),
    ("Fortaleza", "Fortaleza"),
    (42, 42),
])
def test_formatar_valor(valor, esperado):
    assert ma.formatar_valor(valor) == esperado


# ---------------------------------------------------------------------------
# obter_estatisticas (lógica pura sobre geojson)
# ---------------------------------------------------------------------------

def test_obter_estatisticas_sem_dados_retorna_zeros():
    stats = ma.obter_estatisticas(None)
    assert stats == {"total_assentamentos": 0, "area_total": 0, "area_media": 0}


def test_obter_estatisticas_calcula_totais():
    geojson = {
        "features": [
            {"properties": {"tipo_assentamento": "estadual", "area": 10.0}},
            {"properties": {"tipo_assentamento": "federal", "area": 30.0}},
        ]
    }
    stats = ma.obter_estatisticas(geojson)
    assert stats["total_assentamentos"] == 2
    assert stats["area_total"] == 40.0
    assert stats["area_media"] == 20.0


def test_obter_estatisticas_filtra_por_tipo():
    geojson = {
        "features": [
            {"properties": {"tipo_assentamento": "estadual", "area": 10.0}},
            {"properties": {"tipo_assentamento": "federal", "area": 30.0}},
        ]
    }
    stats = ma.obter_estatisticas(geojson, tipo_filtrado="federal")
    assert stats["total_assentamentos"] == 1
    assert stats["area_total"] == 30.0


def test_obter_estatisticas_ignora_area_invalida():
    geojson = {
        "features": [
            {"properties": {"tipo_assentamento": "estadual", "area": "Não Disponível"}},
            {"properties": {"tipo_assentamento": "estadual", "area": "abc"}},
            {"properties": {"tipo_assentamento": "estadual", "area": 10.0}},
        ]
    }
    stats = ma.obter_estatisticas(geojson)
    assert stats["total_assentamentos"] == 3  # conta todas as features
    assert stats["area_total"] == 10.0        # mas só soma áreas válidas


# ---------------------------------------------------------------------------
# carregar_geojson / obter_municipios (chamadas HTTP mockadas)
# ---------------------------------------------------------------------------

def test_carregar_geojson_sucesso(mocked_miniserver):
    result = ma.carregar_geojson(municipio="fortaleza")
    assert result == SAMPLE_ASSENTAMENTOS_GEOJSON


def test_carregar_geojson_erro_retorna_none(requests_mock):
    requests_mock.get(
        f"{ma.DATA_SERVICE_URL}/geojson_assentamentos",
        status_code=500,
    )
    assert ma.carregar_geojson(municipio="fortaleza") is None


def test_obter_municipios_sucesso(mocked_miniserver):
    assert ma.obter_municipios() == ["fortaleza"]


def test_obter_municipios_erro_retorna_lista_vazia(requests_mock):
    requests_mock.get(
        f"{ma.DATA_SERVICE_URL}/assentamentos_municipios",
        exc=__import__("requests").exceptions.ConnectionError,
    )
    assert ma.obter_municipios() == []
