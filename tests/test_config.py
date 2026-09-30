"""Testes de modules/config.py: origem e precedência do JWT_SECRET."""
import pytest

from modules import config


@pytest.fixture
def semAmbiente(monkeypatch):
    monkeypatch.setattr(config, "_JWT_SECRET_DO_AMBIENTE", None)
    monkeypatch.delenv("JWT_SECRET", raising=False)


def test_valorCapturadoNaImportacaoVenceOSecretsToml(semAmbiente, monkeypatch):
    # Simula o Streamlit tendo copiado o secrets.toml para os.environ depois da importação.
    monkeypatch.setattr(config, "_JWT_SECRET_DO_AMBIENTE", "do-container")
    monkeypatch.setenv("JWT_SECRET", "do-arquivo")
    monkeypatch.setattr(config.st, "secrets", {"JWT_SECRET": "do-arquivo"}, raising=False)
    assert config.obterSegredoJwt() == "do-container"


def test_variavelDeAmbienteTemPrecedenciaSobreSecrets(semAmbiente, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "do-ambiente")
    monkeypatch.setattr(config.st, "secrets", {"JWT_SECRET": "do-arquivo"}, raising=False)
    assert config.obterSegredoJwt() == "do-ambiente"


def test_secretsTomlUsadoQuandoNaoHaAmbiente(semAmbiente, monkeypatch):
    monkeypatch.setattr(config.st, "secrets", {"JWT_SECRET": "do-arquivo"}, raising=False)
    assert config.obterSegredoJwt() == "do-arquivo"


def test_semSegredoGeraErroComMensagemClara(semAmbiente, monkeypatch):
    monkeypatch.setattr(config.st, "secrets", {}, raising=False)
    with pytest.raises(config.ErroConfiguracao, match="JWT_SECRET"):
        config.obterSegredoJwt()


def test_valoresVaziosContamComoAusentes(semAmbiente, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "   ")
    monkeypatch.setattr(config.st, "secrets", {"JWT_SECRET": ""}, raising=False)
    with pytest.raises(config.ErroConfiguracao):
        config.obterSegredoJwt()


def test_urlPadraoDoMiniserverNaoTemPrefixoApi():
    assert not config.DATA_SERVICE_URL.endswith("/api")


def test_ttlDosDadosEDeUmDia():
    assert config.TTL_DADOS == 24 * 60 * 60
