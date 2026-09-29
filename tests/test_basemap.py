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
def _semSnapshotDoAmbiente(monkeypatch):
    """Zera o valor capturado na importação do módulo.

    `basemap` guarda a variável de ambiente lida no import; sem zerar isso, o
    ambiente da máquina que roda a suíte vazaria para dentro dos testes.
    """
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", None)


@pytest.fixture
def semSecrets(monkeypatch):
    """Remove a chave do ambiente e de st.secrets."""
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(
        basemap.st, "secrets", {}, raising=False
    )


@pytest.fixture
def comEnv(monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "chave_do_ambiente")
    return "chave_do_ambiente"


# ---------------------------------------------------------------------------
# Origem da chave
# ---------------------------------------------------------------------------

def test_chaveVemDaVariavelDeAmbiente(semSecrets, comEnv):
    assert basemap.obterChaveCarto() == "chave_do_ambiente"


def test_chaveVemDeStSecretsQuandoNaoHaEnv(monkeypatch):
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_do_secrets"}, raising=False
    )
    assert basemap.obterChaveCarto() == "chave_do_secrets"


def test_variavelDeAmbienteTemPrecedenciaSobreSecrets(monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "chave_do_ambiente")
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_do_secrets"}, raising=False
    )
    assert basemap.obterChaveCarto() == "chave_do_ambiente"


def test_semChaveConfiguradaRetornaNone(semSecrets):
    assert basemap.obterChaveCarto() is None


def test_chaveVaziaOuSoEspacosContaComoAusente(semSecrets, monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "   ")
    assert basemap.obterChaveCarto() is None


def test_chaveVaziaEmStSecretsContaComoAusente(monkeypatch):
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(basemap.st, "secrets", {"CARTO_API_KEY": ""}, raising=False)
    assert basemap.obterChaveCarto() is None

    url, _ = basemap.obterTilesBasemap("positron")
    assert "openstreetmap.org" in url


# ---------------------------------------------------------------------------
# Regressão: o Streamlit sobrescreve os.environ com o conteúdo do secrets.toml
# (Secrets._maybe_set_environment_variable). Sem o valor capturado na
# importação, um secrets.toml com CARTO_API_KEY vazia apagaria a chave que o
# Portainer injeta no container, e o mapa cairia para OpenStreetMap em produção
# sem nenhum erro visível.
# ---------------------------------------------------------------------------

def test_secretsVazioNaoApagaAChaveDoAmbiente(monkeypatch):
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", "chave_do_portainer")
    # Estado após o Streamlit ter copiado o secrets.toml vazio para os.environ.
    monkeypatch.setenv("CARTO_API_KEY", "")
    monkeypatch.setattr(basemap.st, "secrets", {"CARTO_API_KEY": ""}, raising=False)

    assert basemap.obterChaveCarto() == "chave_do_portainer"
    url, _ = basemap.obterTilesBasemap("positron")
    assert "key=chave_do_portainer" in url


def test_secretsDesatualizadoNaoSobrepoeAChaveDoAmbiente(monkeypatch):
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", "chave_do_portainer")
    # O Streamlit teria sobrescrito os.environ com a chave antiga do arquivo.
    monkeypatch.setenv("CARTO_API_KEY", "chave_antiga_do_secrets")
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_antiga_do_secrets"}, raising=False
    )

    assert basemap.obterChaveCarto() == "chave_do_portainer"


def test_semAmbienteAChaveDoSecretsAindaEUsada(monkeypatch):
    """No dev local não há variável de ambiente, e o secrets.toml deve valer."""
    monkeypatch.setattr(basemap, "_CARTO_API_KEY_DO_AMBIENTE", None)
    monkeypatch.delenv("CARTO_API_KEY", raising=False)
    monkeypatch.setattr(
        basemap.st, "secrets", {"CARTO_API_KEY": "chave_local"}, raising=False
    )

    assert basemap.obterChaveCarto() == "chave_local"


def test_secretsTomlDoProjetoNaoDeclaraCartoApiKey():
    """Garante que o arquivo real em disco não reintroduza a sobrescrita."""
    import tomllib
    from pathlib import Path

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


def test_chaveDoAmbienteENormalizada(semSecrets, monkeypatch):
    monkeypatch.setenv("CARTO_API_KEY", "  chave_com_espacos  ")
    assert basemap.obterChaveCarto() == "chave_com_espacos"


def test_stSecretsAusenteNaoQuebra(monkeypatch):
    """Streamlit levanta exceção ao ler secrets quando não há secrets.toml."""
    monkeypatch.delenv("CARTO_API_KEY", raising=False)

    class SecretsQuebrado:
        def __getitem__(self, chave):
            raise FileNotFoundError("nenhum secrets.toml neste ambiente")

    monkeypatch.setattr(basemap.st, "secrets", SecretsQuebrado(), raising=False)
    assert basemap.obterChaveCarto() is None


# ---------------------------------------------------------------------------
# URL dos tiles
# ---------------------------------------------------------------------------

def test_urlCarregaAApiKey(semSecrets, comEnv):
    url, _ = basemap.obterTilesBasemap("positron")
    assert "basemaps.cartocdn.com" in url
    assert url.endswith("?key=chave_do_ambiente")


def test_urlPreservaPlaceholdersDoLeaflet(semSecrets, comEnv):
    url, _ = basemap.obterTilesBasemap("positron")
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
def test_cadaEstiloApontaParaOCaminhoCerto(semSecrets, comEnv, estilo, trecho):
    url, _ = basemap.obterTilesBasemap(estilo)
    assert trecho in url


def test_estiloDesconhecidoLevantaErro(semSecrets, comEnv):
    with pytest.raises(ValueError):
        basemap.obterTilesBasemap("estilo_que_nao_existe")


def test_atribuicaoDaCartoPresenteQuandoHaChave(semSecrets, comEnv):
    _, attr = basemap.obterTilesBasemap("positron")
    assert "CARTO" in attr
    assert "OpenStreetMap" in attr


# ---------------------------------------------------------------------------
# Alternativa sem chave
# ---------------------------------------------------------------------------

def test_semChaveCaiParaOpenstreetmap(semSecrets):
    url, attr = basemap.obterTilesBasemap("positron")
    assert "openstreetmap.org" in url
    assert "cartocdn" not in url
    assert "OpenStreetMap" in attr


def test_alternativaNaoCarregaParametroKey(semSecrets):
    url, _ = basemap.obterTilesBasemap("voyager")
    assert "key=" not in url


# ---------------------------------------------------------------------------
# Integração com folium
# ---------------------------------------------------------------------------

def test_criarMapaRenderizaUrlComAChave(semSecrets, comEnv):
    mapa = basemap.criarMapa(location=[-5.2, -39.5], zoom_start=8)
    html = mapa.get_root().render()
    assert "key=chave_do_ambiente" in html


def test_criarMapaIgnoraTilesPassadoPeloChamador(semSecrets, comEnv):
    """Evita que uma chamada antiga com tiles="cartodbpositron" volte a montar
    a URL sem a API key."""
    mapa = basemap.criarMapa(
        location=[-5.2, -39.5], zoom_start=8, tiles="cartodbpositron"
    )
    html = mapa.get_root().render()
    assert "key=chave_do_ambiente" in html
    assert "cartodb-basemaps" not in html


def test_criarMapaNaoAdicionaCamadaBaseDuplicada(semSecrets, comEnv):
    mapa = basemap.criarMapa(location=[-5.2, -39.5], zoom_start=8)
    camadas = [
        filho
        for filho in mapa._children.values()
        if isinstance(filho, folium.TileLayer)
    ]
    assert len(camadas) == 1


def test_apiKeyNaoViraRotuloNoControleDeCamadas(semSecrets, comEnv):
    """Sem `name` explícito o folium usaria a URL do tile como nome da camada,
    exibindo a API key no controle de camadas."""
    mapa = basemap.criarMapa(location=[-5.2, -39.5], zoom_start=8)
    folium.LayerControl().add_to(mapa)
    html = mapa.get_root().render()
    assert "chave_do_ambiente" not in html.split("base_layers")[-1][:2000]


def test_adicionarBasemapDevolveACamada(semSecrets, comEnv):
    mapa = folium.Map(location=[-5.2, -39.5], zoom_start=8, tiles=None)
    camada = basemap.adicionarBasemap(mapa, estilo="voyager")
    assert isinstance(camada, folium.TileLayer)
    assert camada.get_name() in {c.get_name() for c in mapa._children.values()}


def test_criarMapaRepassaOpcoesDoFolium(semSecrets, comEnv):
    mapa = basemap.criarMapa(
        location=[-5.2, -39.5], zoom_start=8, control_scale=True, prefer_canvas=True
    )
    assert mapa.location == [-5.2, -39.5]
