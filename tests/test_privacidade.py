"""Testes de modules/privacidade.py: nome de proprietário conforme a LGPD e escape de HTML."""
import pandas as pd
import pytest

from modules.privacidade import (
    TEXTO_NAO_INFORMADO, TEXTO_NOME_PROTEGIDO, ehPessoaJuridica, escaparColunasTexto,
    escaparHtml, escaparPropriedades, nomeProprietarioExibivel,
)


@pytest.mark.parametrize("nome", [
    "José da Silva",
    "MARIA DAS GRAÇAS PEREIRA",
    "Ricardo Sá Benevides",
    "JOAO DE SA",
    "Espólio de Fulano de Tal",
    "JOAO DA SILVA ME",
    "MARIA SOUZA MEI",
    "PEDRO ALVES EIRELI",
    "Lucia Ciarlini",
])
def test_pessoaFisicaFicaOculta(nome):
    assert not ehPessoaJuridica(nome)
    assert nomeProprietarioExibivel(nome) == TEXTO_NOME_PROTEGIDO


@pytest.mark.parametrize("nome", [
    "Agropecuária Boa Vista Ltda",
    "EMPRESA X S/A",
    "Energia dos Ventos S.A.",
    "ASSOCIAÇÃO DOS PEQUENOS PRODUTORES DO SÍTIO X",
    "Prefeitura Municipal de Canindé",
    "ESTADO DO CEARÁ",
    "Cooperativa Agrícola do Vale",
    "INSTITUTO DE DESENVOLVIMENTO AGRÁRIO DO CEARÁ - IDACE",
    "União Federal",
])
def test_pessoaJuridicaEEntePublicoSaoExibidos(nome):
    assert ehPessoaJuridica(nome)
    assert nomeProprietarioExibivel(nome) == nome


@pytest.mark.parametrize("valor", [None, "", "   ", "nan", "null", float("nan")])
def test_nomeAusenteViraNaoInformado(valor):
    assert nomeProprietarioExibivel(valor) == TEXTO_NAO_INFORMADO


def test_escaparHtmlNeutralizaMarcacao():
    assert escaparHtml('<script>alert("x")</script>') == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
    assert escaparHtml(10.5) == 10.5


def test_escaparPropriedadesNaoAlteraOOriginal():
    original = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"nome": "<b>x</b>", "area": 3}, "geometry": {"type": "Point", "coordinates": [0, 0]}}
    ]}
    copia = escaparPropriedades(original)
    assert copia["features"][0]["properties"] == {"nome": "&lt;b&gt;x&lt;/b&gt;", "area": 3}
    assert original["features"][0]["properties"]["nome"] == "<b>x</b>"


def test_escaparPropriedadesAceitaVazio():
    assert escaparPropriedades(None) == {"type": "FeatureCollection", "features": []}


def test_escaparColunasTextoDevolveCopia():
    df = pd.DataFrame({"nome": ["<i>a</i>"], "valor": [1]})
    resultado = escaparColunasTexto(df, ["nome", "inexistente"])
    assert resultado["nome"].iloc[0] == "&lt;i&gt;a&lt;/i&gt;"
    assert df["nome"].iloc[0] == "<i>a</i>"
