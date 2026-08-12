"""Testes da camada de dados/API: modules/data_loader.py

Cobre parsing e tratamento de erro de _fetch_from_api e das funções públicas
que dependem dela (load_csv_data, load_municipios, validate_data, fetch_*),
usando requests_mock para simular o terraGeoDataMiniServer (sucesso, erro
HTTP, timeout e JSON malformado) -- sem exigir um backend real.
"""
import re

import jwt
import pandas as pd
import pytest
import requests
import requests_mock as requests_mock_module

from modules import data_loader as dl
from tests.conftest import SAMPLE_LOTE, make_lote


BASE = dl.DATA_SERVICE_URL  # http://localhost:8000 (sem sufixo /api)


def url(endpoint):
    return f"{BASE}/{endpoint}"


# ---------------------------------------------------------------------------
# create_jwt_token
# ---------------------------------------------------------------------------

def test_create_jwt_token_is_valid_and_signed():
    token = dl.create_jwt_token()
    payload = jwt.decode(token, dl.JWT_SECRET, algorithms=[dl.JWT_ALGORITHM])
    assert payload["sub"] == "streamlit_app"
    assert "exp" in payload and "iat" in payload


# ---------------------------------------------------------------------------
# _fetch_from_api
# ---------------------------------------------------------------------------

def test_fetch_from_api_success_returns_json(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["A", "B"]})
    result = dl._fetch_from_api("regioes")
    assert result == {"regioes": ["A", "B"]}


def test_fetch_from_api_sends_bearer_token(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": []})
    dl._fetch_from_api("regioes")
    sent_headers = requests_mock.last_request.headers
    assert sent_headers["Authorization"].startswith("Bearer ")


def test_fetch_from_api_version_endpoint_404_returns_default(requests_mock):
    requests_mock.get(url("version"), status_code=404)
    result = dl._fetch_from_api("version")
    assert result == {"data_version": "1.0.0-default"}


def test_fetch_from_api_version_endpoint_timeout_returns_fallback(requests_mock):
    requests_mock.get(url("version"), exc=requests.exceptions.Timeout)
    result = dl._fetch_from_api("version")
    assert result == {"data_version": "1.0.0-fallback"}


def test_fetch_from_api_http_error_raises_when_no_backup(requests_mock, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # garante que backup/<endpoint>.json não existe
    requests_mock.get(url("dados_fundiarios"), status_code=500)
    with pytest.raises(requests.exceptions.RequestException):
        dl._fetch_from_api("dados_fundiarios")


def test_fetch_from_api_malformed_json_raises(requests_mock, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    requests_mock.get(url("dados_fundiarios"), text="isso nao eh json{{{")
    with pytest.raises(requests.exceptions.RequestException):
        dl._fetch_from_api("dados_fundiarios")


def test_fetch_from_api_uses_local_backup_on_failure(requests_mock, tmp_path, monkeypatch):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "dados_fundiarios.json").write_text('{"fallback": true}')
    monkeypatch.chdir(tmp_path)

    requests_mock.get(url("dados_fundiarios"), status_code=503)
    result = dl._fetch_from_api("dados_fundiarios")
    assert result == {"fallback": True}


# ---------------------------------------------------------------------------
# _fetch_regiao_data / _fetch_all_regions_data
# ---------------------------------------------------------------------------

def test_fetch_regiao_data_returns_list_on_success(requests_mock):
    requests_mock.get(
        re.compile(re.escape(url("dados_fundiarios"))),
        json=[SAMPLE_LOTE],
    )
    data = dl._fetch_regiao_data("Regiao Teste")
    assert data == [SAMPLE_LOTE]


def test_fetch_regiao_data_returns_empty_list_when_not_a_list(requests_mock):
    requests_mock.get(
        re.compile(re.escape(url("dados_fundiarios"))),
        json={"unexpected": "shape"},
    )
    assert dl._fetch_regiao_data("Regiao Teste") == []


def test_fetch_regiao_data_returns_empty_list_on_error(requests_mock):
    requests_mock.get(
        re.compile(re.escape(url("dados_fundiarios"))),
        status_code=500,
    )
    assert dl._fetch_regiao_data("Regiao Teste") == []


def test_fetch_all_regions_data_aggregates_and_skips_failures(requests_mock):
    def responder(request, context):
        regiao = request.qs.get("regiao", [None])[0]
        if regiao == "boa":
            return [SAMPLE_LOTE]
        context.status_code = 500
        return {}

    requests_mock.get(re.compile(re.escape(url("dados_fundiarios"))), json=responder)
    result = dl._fetch_all_regions_data(["boa", "ruim"])
    assert result == [SAMPLE_LOTE]


# ---------------------------------------------------------------------------
# load_csv_data
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
    'imovel', 'data_criacao_lote', 'numero_incra',
    'numero_lote', 'area', 'situacao_juridica', 'regiao_administrativa',
    'nome_municipio_original', 'nome_distrito', 'ponto_de_referencia',
    'categoria', 'geometry', 'nome_municipio', 'modulo_fiscal', 'lote_id', 'nome_proprietario'
]


def test_load_csv_data_success_builds_dataframe(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["Regiao Teste"]})
    requests_mock.get(
        re.compile(re.escape(url("dados_fundiarios"))),
        json=[SAMPLE_LOTE, make_lote(area=20.0, modulo_fiscal=4.0)],
    )

    df = dl.load_csv_data("")

    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 2
    # Conversão numérica de area/modulo_fiscal
    assert pd.api.types.is_numeric_dtype(df["area"])
    assert pd.api.types.is_numeric_dtype(df["modulo_fiscal"])
    assert df["area"].tolist() == [10.0, 20.0]


def test_load_csv_data_no_regions_returns_empty_dataframe(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": []})
    df = dl.load_csv_data("")
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_load_csv_data_api_failure_returns_empty_dataframe(requests_mock):
    requests_mock.get(url("regioes"), status_code=500)
    df = dl.load_csv_data("")
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_load_csv_data_coerces_invalid_numeric_to_nan(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["Regiao Teste"]})
    requests_mock.get(
        re.compile(re.escape(url("dados_fundiarios"))),
        json=[make_lote(area="nao-numerico")],
    )
    df = dl.load_csv_data("")
    assert pd.isna(df["area"].iloc[0])


# ---------------------------------------------------------------------------
# load_municipios
# ---------------------------------------------------------------------------

def test_load_municipios_builds_geodataframe(requests_mock):
    from tests.conftest import SAMPLE_MUNI_GEOJSON

    requests_mock.get(url("municipios_todos"), json={"municipios": ["fortaleza"]})
    requests_mock.get(
        re.compile(re.escape(url("geojson_muni"))),
        json=SAMPLE_MUNI_GEOJSON,
    )
    gdf = dl.load_municipios("")
    assert len(gdf) == 1
    assert gdf.iloc[0]["nome_municipio"] == "fortaleza"


def test_load_municipios_returns_empty_geodataframe_when_no_features(requests_mock):
    requests_mock.get(url("municipios_todos"), json={"municipios": []})
    gdf = dl.load_municipios("")
    assert gdf.empty


def test_load_municipios_api_failure_returns_empty_geodataframe(requests_mock):
    requests_mock.get(url("municipios_todos"), status_code=500)
    gdf = dl.load_municipios("")
    assert gdf.empty


# ---------------------------------------------------------------------------
# validate_data (classificação por módulo fiscal)
# ---------------------------------------------------------------------------

def test_validate_data_empty_dataframe_short_circuits():
    df_all, df_class, gdf_inter, df_ctx, counts = dl.validate_data(pd.DataFrame())
    assert df_all.empty and df_class.empty and df_ctx.empty
    assert gdf_inter is None
    assert counts == {}


def test_validate_data_classifies_properties_by_modulo_fiscal(requests_mock):
    requests_mock.get(url("version"), json={"data_version": "9.9.9"})

    df = pd.DataFrame([
        make_lote(area=0.5, modulo_fiscal=5.0),   # < 1 MF -> "Pequena Propriedade < 1 MF"
        make_lote(area=10.0, modulo_fiscal=5.0),  # <= 4 MF -> "Pequena Propriedade"
        make_lote(area=50.0, modulo_fiscal=5.0),  # <= 15 MF -> "Média Propriedade"
        make_lote(area=200.0, modulo_fiscal=5.0),  # > 15 MF -> "Grande Propriedade"
        make_lote(area=None, modulo_fiscal=5.0),   # descartado (area NaN)
    ])

    df_all, df_class, gdf_inter, df_ctx, counts = dl.validate_data(df)

    assert len(df_all) == 5
    assert len(df_class) == 4  # o registro com area NaN é descartado
    assert list(df_class["categoria"]) == [
        "Pequena Propriedade < 1 MF",
        "Pequena Propriedade",
        "Média Propriedade",
        "Grande Propriedade",
    ]
    assert counts["total_carregados"] == 5
    assert counts["validos_classificacao"] == 4
    assert counts["descartados"] == 1
    assert counts["versao_dados"] == "9.9.9"


# ---------------------------------------------------------------------------
# fetch_regioes / fetch_municipios / fetch_geojson_*
# ---------------------------------------------------------------------------

def test_fetch_regioes_success(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["Norte", "Sul"]})
    assert dl.fetch_regioes() == ["Norte", "Sul"]


def test_fetch_municipios_404_returns_empty_list(requests_mock):
    requests_mock.get(url("municipios"), status_code=404)
    assert dl.fetch_municipios("Norte") == []


def test_fetch_municipios_success(requests_mock):
    requests_mock.get(url("municipios"), json={"municipios": ["Fortaleza", "Sobral"]})
    assert dl.fetch_municipios("Norte") == ["Fortaleza", "Sobral"]


def test_fetch_municipios_http_error_raises(requests_mock):
    requests_mock.get(url("municipios"), status_code=500)
    with pytest.raises(requests.exceptions.HTTPError):
        dl.fetch_municipios("Norte")


def test_fetch_geojson_por_regiao_success(requests_mock):
    from tests.conftest import SAMPLE_MUNI_GEOJSON
    requests_mock.get(url("geojson"), json=SAMPLE_MUNI_GEOJSON)
    assert dl.fetch_geojson_por_regiao("Norte") == SAMPLE_MUNI_GEOJSON


def test_fetch_geojson_limites_success(requests_mock):
    from tests.conftest import SAMPLE_MUNI_GEOJSON
    requests_mock.get(url("geojson_muni"), json=SAMPLE_MUNI_GEOJSON)
    assert dl.fetch_geojson_limites("Fortaleza") == SAMPLE_MUNI_GEOJSON
