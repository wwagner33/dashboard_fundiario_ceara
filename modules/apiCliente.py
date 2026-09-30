# modules/apiCliente.py
"""Cliente HTTP único para o terraGeoDataMiniServer.

Reaproveita a conexão (uma ``requests.Session`` por thread) e o token JWT até
perto do vencimento. Não chama nenhuma função ``st.*``: quem decide o que
mostrar ao usuário é a página.
"""

import logging
import threading
from datetime import datetime, timedelta, UTC
from typing import Any

import jwt
import requests

from modules import config

logger = logging.getLogger(__name__)

_MARGEM_RENOVACAO = timedelta(minutes=2)
_local = threading.local()
_travaToken = threading.Lock()
_tokenAtual: str | None = None
_tokenExpiraEm: datetime | None = None


class ErroApi(RuntimeError):
    """Falha ao consultar o miniserver: rede, HTTP ou resposta inválida."""

    def __init__(self, endpoint: str, mensagem: str, status: int | None = None):
        super().__init__(f"{endpoint}: {mensagem}")
        self.endpoint = endpoint
        self.status = status


def gerarToken() -> str:
    """Devolve um token válido, reaproveitando o atual enquanto não estiver perto de vencer."""
    global _tokenAtual, _tokenExpiraEm
    agora = datetime.now(UTC)
    with _travaToken:
        if _tokenAtual and _tokenExpiraEm and agora < _tokenExpiraEm - _MARGEM_RENOVACAO:
            return _tokenAtual
        expiraEm = agora + timedelta(minutes=config.DURACAO_TOKEN_MINUTOS)
        payload = {
            "exp": expiraEm, "iat": agora, "sub": "streamlit_app",
            "aud": config.JWT_AUDIENCIA, "iss": config.JWT_EMISSOR,
        }
        _tokenAtual = jwt.encode(payload, config.obterSegredoJwt(), algorithm=config.JWT_ALGORITHM)
        _tokenExpiraEm = expiraEm
        return _tokenAtual


def descartarToken() -> None:
    """Esquece o token em uso. Útil em testes e depois de rotação de segredo."""
    global _tokenAtual, _tokenExpiraEm
    with _travaToken:
        _tokenAtual = None
        _tokenExpiraEm = None


def _sessao() -> requests.Session:
    sessao = getattr(_local, "sessao", None)
    if sessao is None:
        sessao = requests.Session()
        _local.sessao = sessao
    return sessao


def buscarJson(endpoint: str, parametros: dict | None = None, permitir404: bool = False) -> Any:
    """Faz um GET no miniserver e devolve o JSON da resposta.

    Com ``permitir404=True``, um 404 devolve ``None`` em vez de erro: alguns
    endpoints respondem 404 quando o filtro não encontra nada.
    """
    url = f"{config.DATA_SERVICE_URL}/{endpoint.lstrip('/')}"
    try:
        resposta = _sessao().get(
            url,
            params=parametros,
            headers={"Authorization": f"Bearer {gerarToken()}"},
            timeout=config.REQUEST_TIMEOUT,
        )
    except requests.RequestException as erro:
        logger.warning("Falha de rede ao consultar %s: %s", endpoint, erro)
        raise ErroApi(endpoint, "falha de rede") from erro

    if resposta.status_code == 404 and permitir404:
        return None
    if resposta.status_code == 401:
        descartarToken()
    if not resposta.ok:
        logger.warning("Miniserver respondeu %s em %s", resposta.status_code, endpoint)
        raise ErroApi(endpoint, f"HTTP {resposta.status_code}", resposta.status_code)
    try:
        return resposta.json()
    except ValueError as erro:
        logger.warning("Resposta inválida de %s", endpoint)
        raise ErroApi(endpoint, "resposta não é JSON válido", resposta.status_code) from erro
