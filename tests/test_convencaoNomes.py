"""Garante a convenção de nomes camelCase decidida para o projeto.

- funções, métodos, variáveis e parâmetros em lowerCamelCase;
- classes em UpperCamelCase;
- constantes de módulo em MAIUSCULAS_COM_SUBLINHADO;
- módulos em lowerCamelCase;
- testes com o prefixo ``test_`` exigido pelo pytest, seguido de camelCase.

Nomes de bibliotecas externas (como a fixture ``requests_mock``) são exceção.
"""
import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVOS_CODIGO = [RAIZ / "app.py", *sorted((RAIZ / "modules").glob("*.py"))]
ARQUIVOS_TESTE = sorted((RAIZ / "tests").glob("*.py"))

CAMEL = re.compile(r"^_?[a-z][a-zA-Z0-9]*$")
CLASSE = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")
CONSTANTE = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
TESTE = re.compile(r"^test_[a-z0-9][a-zA-Z0-9]*$")
MODULO = re.compile(r"^(__init__|conftest|test_[a-z][a-zA-Z0-9]*|[a-z][a-zA-Z0-9]*)\.py$")
EXTERNOS = {"requests_mock", "tmp_path", "_", "__version__"}


def _nomeValido(nome, padroes):
    return nome in EXTERNOS or (nome.startswith("__") and nome.endswith("__")) or any(p.match(nome) for p in padroes)


def _problemas(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    problemas = []
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if not isinstance(no, ast.Lambda) and not _nomeValido(no.name, [TESTE, CAMEL]):
                problemas.append(f"função {no.name}")
            argumentos = no.args.posonlyargs + no.args.args + no.args.kwonlyargs
            argumentos += [a for a in (no.args.vararg, no.args.kwarg) if a]
            problemas += [f"parâmetro {a.arg}" for a in argumentos if not _nomeValido(a.arg, [CAMEL])]
        elif isinstance(no, ast.ClassDef) and not _nomeValido(no.name, [CLASSE]):
            problemas.append(f"classe {no.name}")
        elif isinstance(no, (ast.Assign, ast.AnnAssign)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            for nome in _nomesAtribuidos(alvos):
                if not _nomeValido(nome, [CAMEL, CONSTANTE]):
                    problemas.append(f"variável {nome}")
    return sorted(set(problemas))


def _nomesAtribuidos(alvos):
    """Nomes criados por uma atribuição. ``modulo.atributo = x`` não cria nome novo."""
    for alvo in alvos:
        if isinstance(alvo, ast.Name):
            yield alvo.id
        elif isinstance(alvo, (ast.Tuple, ast.List)):
            yield from _nomesAtribuidos(alvo.elts)
        elif isinstance(alvo, ast.Starred):
            yield from _nomesAtribuidos([alvo.value])


@pytest.mark.parametrize("caminho", ARQUIVOS_CODIGO + ARQUIVOS_TESTE, ids=lambda c: c.name)
def test_nomesSeguemAConvencao(caminho):
    assert _problemas(caminho) == []


@pytest.mark.parametrize("caminho", ARQUIVOS_CODIGO + ARQUIVOS_TESTE, ids=lambda c: c.name)
def test_nomeDoArquivoSegueAConvencao(caminho):
    assert MODULO.match(caminho.name), caminho.name
