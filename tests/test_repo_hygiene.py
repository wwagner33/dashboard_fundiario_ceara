"""Testes de "higiene" do repositório para a correção de segurança que:

- Desrastreou `.streamlit/secrets.toml` do git (git rm --cached), mantendo o
  arquivo no disco e adicionando-o ao .gitignore.
- Removeu a senha do Postgres hardcoded (`***SENHA_POSTGRES_REMOVIDA***`) de docker-compose.yml,
  substituindo por `${POSTGRES_PASSWORD}` lido de um `.env` (gitignorado).
- Criou `.streamlit/secrets.toml.example` e `.env.example` como templates.

Estes testes chamam `git` via subprocess (não dependem de um commit ter sido
feito -- `git ls-files` reflete o índice, que já foi atualizado por
`git rm --cached`). Todos os caminhos são resolvidos relativos a este arquivo
de teste, então a suíte roda corretamente independente do cwd usado para
invocar o pytest.
"""
import subprocess
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - fallback para Python < 3.11
    import tomli as tomllib

# Raiz do projeto dashboard_fundiario_ceara (pai de tests/).
REPO_DIR = Path(__file__).resolve().parent.parent

SECRETS_TOML_RELATIVE = ".streamlit/secrets.toml"


def _run_git(*args):
    """Executa um comando git com cwd=REPO_DIR e retorna stdout (texto)."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_secrets_toml_not_tracked_by_git():
    """git ls-files não deve incluir .streamlit/secrets.toml."""
    tracked_files = _run_git("ls-files").splitlines()
    assert SECRETS_TOML_RELATIVE not in tracked_files


def test_docker_compose_does_not_contain_hardcoded_password():
    """docker-compose.yml não deve mais conter a senha antiga em texto puro."""
    docker_compose_path = REPO_DIR / "docker-compose.yml"
    content = docker_compose_path.read_text(encoding="utf-8")
    assert "***SENHA_POSTGRES_REMOVIDA***" not in content


def test_gitignore_contains_secrets_toml_entry():
    """.gitignore deve conter a linha que ignora .streamlit/secrets.toml."""
    gitignore_path = REPO_DIR / ".gitignore"
    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    assert SECRETS_TOML_RELATIVE in lines


def test_secrets_toml_still_exists_on_disk_and_is_valid():
    """O arquivo deve continuar no disco (só desrastreado, não apagado) e
    permanecer um TOML válido contendo a chave JWT_SECRET."""
    secrets_path = REPO_DIR / SECRETS_TOML_RELATIVE
    assert secrets_path.is_file(), (
        f"{secrets_path} não existe mais no disco -- o arquivo deveria ter "
        "sido apenas desrastreado do git (git rm --cached), não apagado."
    )

    with secrets_path.open("rb") as fh:
        data = tomllib.load(fh)

    assert "JWT_SECRET" in data
    assert isinstance(data["JWT_SECRET"], str)
    assert data["JWT_SECRET"] != ""
