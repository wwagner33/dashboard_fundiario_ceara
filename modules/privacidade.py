# modules/privacidade.py
"""Proteção de dados pessoais (LGPD) e escape de HTML para dados vindos da API.

Nome de proprietário
--------------------
A LGPD (Lei 13.709/2018) protege dados de pessoas naturais. O nome de uma
pessoa física é dado pessoal e não é exibido no dashboard. O nome de uma pessoa
jurídica ou de um ente público não é dado pessoal e pode ser exibido.

A distinção é feita pelo próprio nome, de forma conservadora: só é tratado
como pessoa jurídica o nome que termina em ``LTDA`` ou ``S/A`` ou que traz um
termo institucional inequívoco (``ASSOCIAÇÃO``, ``PREFEITURA``, ``ESTADO DO
CEARÁ``...). Na dúvida, o nome fica oculto. Espólio e empresário individual
(ME, MEI, EIRELI), que costumam carregar o nome da pessoa, ficam ocultos.

O mascaramento acontece no servidor do Streamlit, antes de montar o mapa, então
o nome da pessoa física nunca chega ao navegador. O miniserver ainda envia os
nomes ao dashboard; tirá-los da API exige uma nova versão do miniserver.

HTML
----
O folium insere os valores de tooltip com ``innerHTML``, sem escape. Todo texto
vindo da API passa por ``escaparHtml`` antes de entrar num mapa ou num trecho
de HTML.
"""

import html
import re
import unicodedata
from typing import Any
from collections.abc import Iterable

import pandas as pd

TEXTO_NOME_PROTEGIDO = "Pessoa física (protegido pela LGPD)"
TEXTO_NAO_INFORMADO = "Não informado"

_TERMOS_INSTITUCIONAIS = [
    "ASSOCIACAO", "ASSOC", "COOPERATIVA", "SINDICATO", "FUNDACAO", "INSTITUTO",
    "EMPRESA", "COMPANHIA", "CIA", "AGROPECUARIA", "AGROINDUSTRIA", "AGROINDUSTRIAL",
    "INDUSTRIA", "INDUSTRIAL", "COMERCIO", "COMERCIAL", "MINERACAO", "MINERADORA",
    "CONSTRUTORA", "INCORPORADORA", "EMPREENDIMENTOS", "PARTICIPACOES", "HOLDING",
    "CONDOMINIO", "CONSORCIO", "SOCIEDADE", "IGREJA", "PAROQUIA", "DIOCESE",
    "ARQUIDIOCESE", "MITRA", "CONGREGACAO", "PREFEITURA", "MUNICIPIO", "CAMARA MUNICIPAL",
    "ESTADO DO CEARA", "GOVERNO", "UNIAO FEDERAL", "SECRETARIA", "INCRA", "IDACE",
    "DNOCS", "CAGECE", "COGERH", "EMBRAPA", "UNIVERSIDADE", "ESCOLA", "COLEGIO",
    "HOSPITAL", "BANCO", "EOLICA", "ENERGIA",
]
_REGEX_INSTITUCIONAL = re.compile(r"\b(?:" + "|".join(_TERMOS_INSTITUCIONAIS) + r")\b")
# Formas jurídicas no fim do nome. Ficam de fora de propósito:
# - "SA" sem pontuação, porque Sá é sobrenome comum;
# - ME, MEI, EPP e EIRELI, porque o empresário individual costuma usar o
#   próprio nome como razão social, e o nome da pessoa seria exposto.
_REGEX_FORMA_JURIDICA = re.compile(r"(?:\bLTDA\.?|\bS\s?/\s?A\.?|\bS\.A\.?)\s*$")


def _normalizar(texto: str) -> str:
    semAcento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", semAcento.upper()).strip()


def _vazio(valor: Any) -> bool:
    if valor is None:
        return True
    try:
        if pd.isna(valor):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(valor, str) and valor.strip().lower() in ("", "nan", "none", "null")


def ehPessoaJuridica(nome: str | None) -> bool:
    """Indica se o nome identifica com segurança uma pessoa jurídica ou ente público."""
    if _vazio(nome):
        return False
    normalizado = _normalizar(str(nome))
    return bool(_REGEX_FORMA_JURIDICA.search(normalizado) or _REGEX_INSTITUCIONAL.search(normalizado))


def nomeProprietarioExibivel(nome: str | None) -> str:
    """Texto que pode ser mostrado no lugar do nome do proprietário."""
    if _vazio(nome):
        return TEXTO_NAO_INFORMADO
    if ehPessoaJuridica(nome):
        return str(nome).strip()
    return TEXTO_NOME_PROTEGIDO


def escaparHtml(valor: Any) -> Any:
    """Escapa texto para uso seguro em HTML. Outros tipos passam sem alteração."""
    if isinstance(valor, str):
        return html.escape(valor, quote=True)
    return valor


def escaparPropriedades(geojson: dict | None) -> dict:
    """Cópia do FeatureCollection com todo texto das propriedades escapado.

    A geometria é compartilhada com o original, sem cópia, e não é alterada.
    """
    if not geojson:
        return {"type": "FeatureCollection", "features": []}
    copia = {k: v for k, v in geojson.items() if k != "features"}
    copia["features"] = [
        {
            "type": feature.get("type", "Feature"),
            "geometry": feature.get("geometry"),
            "properties": {k: escaparHtml(v) for k, v in (feature.get("properties") or {}).items()},
        }
        for feature in geojson.get("features", [])
    ]
    return copia


def escaparColunasTexto(df: pd.DataFrame, colunas: Iterable[str]) -> pd.DataFrame:
    """Cópia do DataFrame com as colunas de texto indicadas escapadas."""
    copia = df.copy()
    for coluna in colunas:
        if coluna in copia.columns:
            copia[coluna] = copia[coluna].map(escaparHtml)
    return copia
