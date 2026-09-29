"""Testes de modules/repositorio.py: formato dos dados, cache e número de requisições."""
import re

import pandas as pd
import pytest

from modules import apiCliente, config, repositorio
from tests.conftest import GEOJSON_MUNICIPIOS, criarLote, url

TODAS = re.compile("^" + re.escape(config.DATA_SERVICE_URL))


def _chamadas(mock, endpoint):
    return [r for r in mock.request_history if r.path.rstrip("/") == f"/{endpoint}"]


def test_limitesMunicipaisVemDeUmaUnicaRequisicao(miniserverSimulado):
    gdf = repositorio.carregarLimitesMunicipaisGdf()
    chamadas = _chamadas(miniserverSimulado, "geojson_muni")
    assert len(chamadas) == 1
    assert chamadas[0].qs == {"municipio": ["todos"]}
    assert gdf.iloc[0]["nome_municipio"] == "fortaleza"
    assert gdf.crs.to_string() == "EPSG:4326"


def test_limitesVaziosDevolvemGeoDataFrameComColunas(requests_mock):
    requests_mock.get(url("geojson_muni"), json={"type": "FeatureCollection", "features": []})
    gdf = repositorio.carregarLimitesMunicipaisGdf()
    assert gdf.empty
    assert "nome_municipio" in gdf.columns


def test_carregarLotesJuntaTodasAsRegioes(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["A", "B"]})

    def responder(request, context):
        return [criarLote(regiao_administrativa=request.qs["regiao"][0].upper())]

    requests_mock.get(url("dados_fundiarios"), json=responder)
    df = repositorio.carregarLotes()
    assert list(df.columns) == repositorio.COLUNAS_LOTES
    assert sorted(df["regiao_administrativa"]) == ["A", "B"]
    assert pd.api.types.is_numeric_dtype(df["area"])
    assert "geometry" not in df.columns


def test_carregarLotesConverteNumerosInvalidosEmNaN(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["A"]})
    requests_mock.get(url("dados_fundiarios"), json=[criarLote(area="não numérico")])
    assert pd.isna(repositorio.carregarLotes()["area"].iloc[0])


def test_carregarLotesIgnoraRegiaoComFalhaERegistraQual(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["boa", "ruim"]})

    def responder(request, context):
        if request.qs["regiao"][0] == "ruim":
            context.status_code = 500
            return {}
        return [criarLote()]

    requests_mock.get(url("dados_fundiarios"), json=responder)
    df = repositorio.carregarLotes()
    assert len(df) == 1
    assert df.attrs["regioesComFalha"] == ["ruim"]


def test_carregarLotesFalhaQuandoNenhumaRegiaoResponde(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["A"]})
    requests_mock.get(url("dados_fundiarios"), status_code=500)
    with pytest.raises(apiCliente.ErroApi):
        repositorio.carregarLotes()


def test_lotesClassificadosDescartamSemAreaEMantemAVersao(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["A"]})
    requests_mock.get(url("dados_fundiarios"), json=[criarLote(area=0.5), criarLote(area=None)])
    lotes = repositorio.carregarLotes()
    classificados = repositorio.carregarLotesClassificados()
    assert len(classificados) == 1
    assert classificados["categoria"].iloc[0] == "Pequena Propriedade < 1 MF"
    assert repositorio.versaoDados(classificados) == repositorio.versaoDados(lotes)


def test_municipiosDaRegiaoSem404DevolveListaVazia(requests_mock):
    requests_mock.get(url("municipios"), status_code=404)
    assert repositorio.carregarMunicipiosDaRegiao("Norte") == []


def test_geojsonDeLotesPorRegiaoEnviaSoARegiao(requests_mock):
    requests_mock.get(url("geojson"), json={"type": "FeatureCollection", "features": []})
    repositorio.carregarGeojsonLotes(regiao="Cariri")
    assert requests_mock.last_request.qs == {"regiao": ["cariri"]}


def test_geojsonDeLotes404DevolveColecaoVazia(requests_mock):
    requests_mock.get(url("geojson"), status_code=404)
    assert repositorio.carregarGeojsonLotes(municipio="x") == repositorio.GEOJSON_VAZIO


def test_assentamentosEnviamATolerancia(requests_mock):
    requests_mock.get(url("geojson_assentamentos"), json={"type": "FeatureCollection", "features": []})
    repositorio.carregarAssentamentos("todos", 0.001)
    assert requests_mock.last_request.qs == {"municipio": ["todos"], "tolerance": ["0.001"]}


def test_filtrarLimitesMantemSoOsMunicipiosPedidos():
    limites = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"nome_municipio": nome}, "geometry": None} for nome in ("a", "b", "c")
    ]}
    recorte = repositorio.filtrarLimites(limites, ["a", "c"])
    assert [f["properties"]["nome_municipio"] for f in recorte["features"]] == ["a", "c"]


def test_cacheEvitaRequisicaoRepetida(miniserverSimulado):
    repositorio.carregarRegioes()
    repositorio.carregarRegioes()
    assert len(_chamadas(miniserverSimulado, "regioes")) == 1


def test_primeiraCargaCompletaFazUmaRequisicaoPorRegiaoMaisDuas(miniserverSimulado):
    repositorio.carregarLotesClassificados()
    repositorio.carregarLimitesMunicipaisGdf()
    repositorio.carregarLimitesMunicipais()
    numeroDeRegioes = 1
    assert miniserverSimulado.call_count == 2 + numeroDeRegioes
    assert GEOJSON_MUNICIPIOS["features"]
