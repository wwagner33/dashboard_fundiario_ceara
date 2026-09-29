"""Testes de modules/apiCliente.py: token, sessão e tratamento de erro."""
from datetime import datetime, timedelta, UTC

import jwt
import pytest
import requests

from modules import apiCliente, config
from tests.conftest import url


def test_buscarJsonDevolveOCorpoDaResposta(requests_mock):
    requests_mock.get(url("regioes"), json={"regioes": ["A", "B"]})
    assert apiCliente.buscarJson("regioes") == {"regioes": ["A", "B"]}


def test_enviaTokenBearerAssinadoComOSegredo(requests_mock):
    requests_mock.get(url("regioes"), json={})
    apiCliente.buscarJson("regioes")
    cabecalho = requests_mock.last_request.headers["Authorization"]
    assert cabecalho.startswith("Bearer ")
    payload = jwt.decode(cabecalho.split(" ", 1)[1], config.obterSegredoJwt(), algorithms=[config.JWT_ALGORITHM])
    assert payload["sub"] == "streamlit_app"


def test_reaproveitaOTokenEntreChamadas(requests_mock):
    requests_mock.get(url("regioes"), json={})
    apiCliente.buscarJson("regioes")
    primeiro = requests_mock.last_request.headers["Authorization"]
    apiCliente.buscarJson("regioes")
    assert requests_mock.last_request.headers["Authorization"] == primeiro


def test_renovaOTokenPertoDoVencimento(monkeypatch):
    apiCliente.gerarToken()
    quaseVencendo = datetime.now(UTC) + timedelta(seconds=30)
    monkeypatch.setattr(apiCliente, "_tokenExpiraEm", quaseVencendo)
    apiCliente.gerarToken()
    assert apiCliente._tokenExpiraEm > quaseVencendo + timedelta(minutes=20)


def test_enviaOsParametrosDaConsulta(requests_mock):
    requests_mock.get(url("municipios"), json={"municipios": []})
    apiCliente.buscarJson("municipios", {"regiao": "Cariri"})
    assert requests_mock.last_request.qs == {"regiao": ["cariri"]}


def test_erroHttpViraErroApiComStatus(requests_mock):
    requests_mock.get(url("regioes"), status_code=500)
    with pytest.raises(apiCliente.ErroApi) as erro:
        apiCliente.buscarJson("regioes")
    assert erro.value.status == 500


def test_falhaDeRedeViraErroApi(requests_mock):
    requests_mock.get(url("regioes"), exc=requests.exceptions.Timeout)
    with pytest.raises(apiCliente.ErroApi):
        apiCliente.buscarJson("regioes")


def test_jsonInvalidoViraErroApi(requests_mock):
    requests_mock.get(url("regioes"), text="isso não é json{{")
    with pytest.raises(apiCliente.ErroApi):
        apiCliente.buscarJson("regioes")


def test_404PermitidoDevolveNone(requests_mock):
    requests_mock.get(url("municipios"), status_code=404)
    assert apiCliente.buscarJson("municipios", permitir404=True) is None


def test_404NaoPermitidoGeraErro(requests_mock):
    requests_mock.get(url("municipios"), status_code=404)
    with pytest.raises(apiCliente.ErroApi):
        apiCliente.buscarJson("municipios")


def test_respostaNaoAutorizadaDescartaOToken(requests_mock):
    requests_mock.get(url("regioes"), status_code=401)
    with pytest.raises(apiCliente.ErroApi):
        apiCliente.buscarJson("regioes")
    assert apiCliente._tokenAtual is None


def test_mensagemDoErroNaoExpoeAUrlInterna(requests_mock):
    requests_mock.get(url("regioes"), status_code=500)
    with pytest.raises(apiCliente.ErroApi) as erro:
        apiCliente.buscarJson("regioes")
    assert config.DATA_SERVICE_URL not in str(erro.value)
