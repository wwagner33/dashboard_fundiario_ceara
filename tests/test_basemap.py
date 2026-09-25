"""Testes da camada base dos mapas (modules/basemap.py).

Cobrem a mudança da CARTO que passou a exigir API key nos tiles raster:

- a chave sai da variável de ambiente CARTO_API_KEY, com st.secrets como
  alternativa e precedência da variável de ambiente;
- a URL dos tiles carrega o parâmetro `key` e preserva os placeholders do
  Leaflet ({z}/{x}/{y});
- sem chave configurada o dashboard cai para OpenStreetMap em vez de exibir a
  marca d'água;
- a atribuição da CARTO e do OpenStreetMap continua presente;
- a API key não vaza como rótulo de camada no controle de camadas.

Nota: `.streamlit/secrets.toml` existe no disco com valores de teste, então
os testes que exercitam a ausência de chave precisam neutralizar também o
st.secrets, não só a variável de ambiente.
"""
import folium
import pytest

from modules import basemap


@pytest.fixture(autouse=True)
def _sem_snapshot_do_ambiente(monkeypatch):
    """Zera o valor capturado na importação do módulo.

    `basemap` guarda a variável de ambiente lida no import; sem zerar isso, o
    ambiente da máquina que roda a suíte vazaria para dentro dos testes.
    """
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", None)


@pytest.fixture
def sem_secrets(monkeypatch):
    """Remove a chave do ambiente e de st.secrets."""
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(
        basemap.st, "secrets", {}, raising=False
    )


@pytest.fixture
def com_env(monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "chave_do_ambiente")
    return "chave_do_ambiente"


# ---------------------------------------------------------------------------
# Origem da chave
# ---------------------------------------------------------------------------

def test_chave_vem_da_variavel_de_ambiente(sem_secrets, com_env):
    assert basemap.get_carto_api_key() == "chave_do_ambiente"


def test_chave_vem_de_st_secrets_quando_nao_ha_env(monkeypatch):
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_do_secrets"}, raising=False
    )
    assert basemap.get_carto_api_key() == "chave_do_secrets"


def test_variavel_de_ambiente_tem_precedencia_sobre_secrets(monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "chave_do_ambiente")
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_do_secrets"}, raising=False
    )
    assert basemap.get_carto_api_key() == "chave_do_ambiente"


def test_sem_chave_configurada_retorna_none(sem_secrets):
    assert basemap.get_carto_api_key() is None


def test_chave_vazia_ou_so_espacos_conta_como_ausente(sem_secrets, monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "   ")
    assert basemap.get_carto_api_key() is None


def test_chave_vazia_em_st_secrets_conta_como_ausente(monkeypatch):
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(basemap.st, "secrets", {"CARTO_API_KEY": ""}, raising=False)
    assert basemap.get_carto_api_key() is None

    url, _ = basemap.basemap_tiles("positron")
    assert "openstreetmap.org" in url


# ---------------------------------------------------------------------------
# Regressão: o Streamlit sobrescreve os.environ com o conteúdo do secrets.toml
# (Secrets._maybe_set_environment_variable). Sem o valor capturado na
# importação, um secrets.toml com CARTO_API_KEY vazia apagaria a chave que o
# Portainer injeta no container, e o mapa cairia para OpenStreetMap em produção
# sem nenhum erro visível.
# ---------------------------------------------------------------------------

def test_secrets_vazio_nao_apaga_a_chave_do_ambiente(monkeypatch):
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", "chave_do_portainer")
    # Estado após o Streamlit ter copiado o secrets.toml vazio para os.environ.
    monkeypatch.setenv("CARTO_API_KEY", "")
    monkeypatch.setattr(basemap.st, "secrets", {"CARTO_API_KEY": ""}, raising=False)

    assert basemap.get_carto_api_key() == "chave_do_portainer"
    url, _ = basemap.basemap_tiles("positron")
    assert "key=chave_do_portainer" in url


def test_secrets_desatualizado_nao_sobrepoe_a_chave_do_ambiente(monkeypatch):
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", "chave_do_portainer")
    # O Streamlit teria sobrescrito os.environ com a chave antiga do arquivo.
    monkeypatch.setenv("CARTO_API_KEY", "chave_antiga_do_secrets")
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_antiga_do_secrets"}, raising=False
    )

    assert basemap.get_carto_api_key() == "chave_do_portainer"


def test_sem_ambiente_a_chave_do_secrets_ainda_e_usada(monkeypatch):
    """No dev local não há variável de ambiente, e o secrets.toml deve valer."""
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", None)
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_local"}, raising=False
    )

    assert basemap.get_carto_api_key() == "chave_local"


def test_secrets_toml_do_projeto_nao_declara_carto_api_key():
    """Garante que o arquivo real em disco não reintroduza a sobrescrita."""
    import sys
    from pathlib import Path

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover
        import tomli as tomllib

    caminho = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
    if not caminho.is_file():
        pytest.skip("secrets.toml não existe neste ambiente")

    with caminho.open("rb") as fh:
        dados = tomllib.load(fh)

    assert "CARTO_API_KEY" not in dados, (
        "CARTO_API_KEY declarada em .streamlit/secrets.toml sobrescreve a "
        "variável de ambiente do container (o Streamlit copia segredos para "
        "os.environ). Defina a chave apenas como variável de ambiente."
    )


def test_chave_do_ambiente_e_normalizada(sem_secrets, monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "  chave_com_espacos  ")
    assert basemap.get_carto_api_key() == "chave_com_espacos"


def test_st_secrets_ausente_nao_quebra(monkeypatch):
    """Streamlit levanta exceção ao ler secrets quando não há secrets.toml."""
    monkeypatch.delenv("CARTO_API_KEY", raising=False)

    class SecretsQuebrado:
        def __getitem__(self, chave):
            raise FileNotFoundError("nenhum secrets.toml neste ambiente")

    monkeypatch.setattr(basemap.st, "secrets", SecretsQuebrado(), raising=False)
    assert basemap.get_carto_api_key() is None


# ---------------------------------------------------------------------------
# URL dos tiles
# ---------------------------------------------------------------------------

def test_url_carrega_a_api_key(sem_secrets, com_env):
    url, _ = basemap.basemap_tiles("positron")
    assert "basemaps.cartocdn.com" in url
    assert url.endswith("?key=chave_do_ambiente")


def test_url_preserva_placeholders_do_leaflet(sem_secrets, com_env):
    url, _ = basemap.basemap_tiles("positron")
    for placeholder in ("{z}", "{x}", "{y}"):
        assert placeholder in url


@pytest.mark.parametrize(
    "estilo,trecho",
    [
        ("positron", "/light_all/"),
        ("positron_nolabels", "/light_nolabels/"),
        ("dark_matter", "/dark_all/"),
        ("voyager", "/rastertiles/voyager/"),
    ],
)
def test_cada_estilo_aponta_para_o_caminho_certo(sem_secrets, com_env, estilo, trecho):
    url, _ = basemap.basemap_tiles(estilo)
    assert trecho in url


def test_estilo_desconhecido_levanta_erro(sem_secrets, com_env):
    with pytest.raises(ValueError):
        basemap.basemap_tiles("estilo_que_nao_existe")


def test_atribuicao_da_carto_presente_quando_ha_chave(sem_secrets, com_env):
    _, attr = basemap.basemap_tiles("positron")
    assert "CARTO" in attr
    assert "OpenStreetMap" in attr


# ---------------------------------------------------------------------------
# Alternativa sem chave
# ---------------------------------------------------------------------------

def test_sem_chave_cai_para_openstreetmap(sem_secrets):
    url, attr = basemap.basemap_tiles("positron")
    assert "openstreetmap.org" in url
    assert "cartocdn" not in url
    assert "OpenStreetMap" in attr


def test_alternativa_nao_carrega_parametro_key(sem_secrets):
    url, _ = basemap.basemap_tiles("voyager")
    assert "key=" not in url


# ---------------------------------------------------------------------------
# Integração com folium
# ---------------------------------------------------------------------------

def test_criar_mapa_renderiza_url_com_a_chave(sem_secrets, com_env):
    mapa = basemap.criar_mapa(location=[-5.2, -39.5], zoom_start=8)
    html = mapa.get_root().render()
    assert "key=chave_do_ambiente" in html


def test_criar_mapa_ignora_tiles_passado_pelo_chamador(sem_secrets, com_env):
    """Evita que uma chamada antiga com tiles="cartodbpositron" volte a montar
    a URL sem a API key."""
    mapa = basemap.criar_mapa(
        location=[-5.2, -39.5], zoom_start=8, tiles="cartodbpositron"
    )
    html = mapa.get_root().render()
    assert "key=chave_do_ambiente" in html
    assert "cartodb-basemaps" not in html


def test_criar_mapa_nao_adiciona_camada_base_duplicada(sem_secrets, com_env):
    mapa = basemap.criar_mapa(location=[-5.2, -39.5], zoom_start=8)
    camadas = [
        filho
        for filho in mapa._children.values()
        if isinstance(filho, folium.TileLayer)
    ]
    assert len(camadas) == 1


def test_api_key_nao_vira_rotulo_no_controle_de_camadas(sem_secrets, com_env):
    """Sem `name` explícito o folium usaria a URL do tile como nome da camada,
    exibindo a API key no controle de camadas."""
    mapa = basemap.criar_mapa(location=[-5.2, -39.5], zoom_start=8)
    folium.LayerControl().add_to(mapa)
    html = mapa.get_root().render()
    assert "chave_do_ambiente" not in html.split("base_layers")[-1][:2000]


def test_adicionar_basemap_devolve_a_camada(sem_secrets, com_env):
    mapa = folium.Map(location=[-5.2, -39.5], zoom_start=8, tiles=None)
    camada = basemap.adicionar_basemap(mapa, estilo="voyager")
    assert isinstance(camada, folium.TileLayer)
    assert camada.get_name() in {c.get_name() for c in mapa._children.values()}


def test_criar_mapa_repassa_opcoes_do_folium(sem_secrets, com_env):
    mapa = basemap.criar_mapa(
        location=[-5.2, -39.5], zoom_start=8, control_scale=True, prefer_canvas=True
    )
    assert mapa.location == [-5.2, -39.5]
