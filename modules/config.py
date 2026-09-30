# modules/config.py
"""Configuração central do dashboard: endereço do miniserver, timeouts e segredo JWT.

O segredo JWT é lido, nesta ordem:

1. variável de ambiente ``JWT_SECRET``, capturada na importação deste módulo;
2. variável de ambiente ``JWT_SECRET`` no momento da chamada;
3. ``st.secrets["JWT_SECRET"]``, vindo de ``.streamlit/secrets.toml``.

Atenção: o ``streamlit run`` carrega o ``secrets.toml`` ao iniciar o servidor,
antes de importar este módulo, e copia cada segredo para ``os.environ``. Se o
arquivo tiver ``JWT_SECRET``, ele sempre vence a variável do container. Em
produção o arquivo fica fora da imagem (ver ``.dockerignore``) e vale a
variável de ambiente. A captura na importação só protege execuções que não
passam pelo servidor, como os testes.
"""

import os

import streamlit as st

JWT_ALGORITHM = "HS256"
# Claims exigidos pelo miniserver desde a versão 1.2.0.
JWT_AUDIENCIA = "terra-geodata-mini-server"
JWT_EMISSOR = "dashboard_fundiario_ceara"
DURACAO_TOKEN_MINUTOS = 30
REQUEST_TIMEOUT = 120  # segundos

# Os dados do miniserver são recarregados uma vez por mês. O dashboard consulta
# /versao_dados a cada TTL_VERSAO segundos e descarta o cache quando a versão
# muda. O TTL de 24 horas fica como segurança para servidores sem esse endpoint.
TTL_DADOS = 24 * 60 * 60
TTL_VERSAO = 5 * 60

DATA_SERVICE_URL = os.environ.get("DATA_SERVICE_URL", "http://localhost:8000").rstrip("/")

_JWT_SECRET_DO_AMBIENTE = os.environ.get("JWT_SECRET")


class ErroConfiguracao(RuntimeError):
    """Configuração obrigatória ausente."""


def _normalizar(valor) -> str | None:
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def obterSegredoJwt() -> str:
    """Devolve o segredo usado para assinar os tokens enviados ao miniserver."""
    for candidato in (_JWT_SECRET_DO_AMBIENTE, os.environ.get("JWT_SECRET")):
        valor = _normalizar(candidato)
        if valor:
            return valor
    try:
        valor = _normalizar(st.secrets["JWT_SECRET"])
    except Exception:
        valor = None
    if valor:
        return valor
    raise ErroConfiguracao(
        "JWT_SECRET não configurado. Defina a variável de ambiente JWT_SECRET "
        "ou a chave JWT_SECRET em .streamlit/secrets.toml."
    )
