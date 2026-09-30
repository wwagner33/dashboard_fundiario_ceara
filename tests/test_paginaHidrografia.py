"""Testes de modules/paginaHidrografia.py: estatísticas e camada de reservatórios."""
import copy

import folium
import pytest

from modules import paginaHidrografia as ph
from tests.conftest import GEOJSON_RESERVATORIOS


def test_estatisticasSemDados():
    assert ph.calcularEstatisticas(None) == {"total": 0, "capacidadeTotalM3": 0, "areaTotalHa": 0}


def test_estatisticasSomamCapacidadeEArea():
    estatisticas = ph.calcularEstatisticas(GEOJSON_RESERVATORIOS)
    assert estatisticas["total"] == 1
    assert estatisticas["capacidadeTotalM3"] == pytest.approx(1000.0)
    assert estatisticas["areaTotalHa"] == pytest.approx(50.0)


def test_estatisticasIgnoramValoresInvalidos():
    estatisticas = ph.calcularEstatisticas({"features": [{"properties": {"capacid_m3": "abc", "area_ha": "xyz"}}]})
    assert estatisticas == {"total": 1, "capacidadeTotalM3": 0, "areaTotalHa": 0}


def test_camadaDeReservatoriosEscapaONome():
    geojson = copy.deepcopy(GEOJSON_RESERVATORIOS)
    geojson["features"][0]["properties"]["nome"] = "<b>Açude</b>"
    mapa = folium.Map()
    ph.adicionarCamadaReservatorios(mapa, geojson)
    html = mapa.get_root().render()
    assert "&lt;b&gt;Açude&lt;/b&gt;" in html
    assert "<b>Açude</b>" not in html
