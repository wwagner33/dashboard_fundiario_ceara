"""Higiene do repositório: segredos fora do git e da imagem Docker.

Os caminhos são resolvidos a partir deste arquivo, então a suíte roda de
qualquer diretório. O teste do ``secrets.toml`` no disco é pulado quando o
arquivo não existe numa execução de CI, onde ele nunca é criado.
"""
import os
import subprocess
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SECRETS_TOML = ".streamlit/secrets.toml"


def _rodarGit(*argumentos):
    return subprocess.run(["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, check=True).stdout


def test_secretsTomlNaoEstaNoGit():
    assert SECRETS_TOML not in _rodarGit("ls-files").splitlines()


def test_dockerComposeNaoTemSenhaFixa():
    conteudo = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    assert "***SENHA_POSTGRES_REMOVIDA***" not in conteudo
    assert "${POSTGRES_PASSWORD}" in conteudo


def test_gitignoreCobreSegredosEArquivosSemUso():
    linhas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert SECRETS_TOML in linhas
    assert ".env" in linhas
    assert "arquivos-sem-uso/" in linhas


def test_dockerignoreDeixaSegredosEArquivosSemUsoForaDaImagem():
    linhas = (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in linhas
    assert SECRETS_TOML in linhas
    assert "arquivos-sem-uso/" in linhas


def test_secretsTomlLocalContinuaValido():
    caminho = RAIZ / SECRETS_TOML
    if not caminho.is_file() and os.environ.get("CI"):
        pytest.skip("secrets.toml não existe no CI")
    assert caminho.is_file(), "o secrets.toml local sumiu; ele só deveria estar fora do git"
    dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
    assert isinstance(dados.get("JWT_SECRET"), str) and dados["JWT_SECRET"]
