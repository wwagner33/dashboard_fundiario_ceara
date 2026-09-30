"""Testes de modules/paginaAssentamentos.py: filtro por tipo e estatísticas."""
from modules import paginaAssentamentos as pa

GEOJSON = {"features": [
    {"properties": {"tipo_assentamento": "estadual", "area": 10.0}},
    {"properties": {"tipo_assentamento": "federal", "area": 30.0}},
    {"properties": {"tipo_assentamento": "estadual", "area": "Não Disponível"}},
]}


def test_filtrarPorTipo():
    assert len(pa.filtrarPorTipo(GEOJSON, "Federal")["features"]) == 1
    assert len(pa.filtrarPorTipo(GEOJSON, pa.TODOS)["features"]) == 3
    assert pa.filtrarPorTipo(None, "Estadual")["features"] == []


def test_estatisticasSemDados():
    assert pa.calcularEstatisticas(None) == {"totalAssentamentos": 0, "areaTotal": 0, "areaMedia": 0}


def test_estatisticasContamTodosESomamSoAreasValidas():
    estatisticas = pa.calcularEstatisticas(GEOJSON)
    assert estatisticas["totalAssentamentos"] == 3
    assert estatisticas["areaTotal"] == 40.0
    assert estatisticas["areaMedia"] == 20.0
