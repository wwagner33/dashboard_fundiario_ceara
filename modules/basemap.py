# modules/basemap.py
"""Camada base (basemap) dos mapas do dashboard, com suporte à API key da CARTO.

Contexto
--------
A partir de 2025 o serviço de tiles *raster* (PNG) da CARTO passou a exigir uma
API key. Sem a chave os tiles continuam sendo servidos, porém com a marca
d'água "API key required" sobre o mapa inteiro.

A chave é lida, nesta ordem:

1. variável de ambiente ``CARTO_API_KEY`` (forma usada em produção/container);
2. ``st.secrets["CARTO_API_KEY"]`` (forma usada em desenvolvimento local, via
   ``.streamlit/secrets.toml``).

Por que a variável de ambiente é lida na importação
---------------------------------------------------
O Streamlit copia todo segredo de tipo simples do ``secrets.toml`` para dentro
de ``os.environ`` (``Secrets._maybe_set_environment_variable``), sobrescrevendo
o que já estivesse lá. Na prática isso inverte a precedência esperada: um
``CARTO_API_KEY`` definido no ``secrets.toml`` passa por cima da variável de
ambiente do container e, pior, um valor vazio no arquivo apaga a chave injetada
pelo Portainer.

Para não depender desse efeito colateral, o valor da variável de ambiente é
capturado aqui no momento da importação, antes que qualquer leitura de
``st.secrets`` aconteça. ``modules/__init__.py`` importa este módulo primeiro,
justamente para garantir essa ordem.

Se nenhuma das duas estiver definida, o dashboard cai automaticamente para os
tiles do OpenStreetMap. A escolha é deliberada: é preferível um mapa com outra
aparência a um mapa coberto por marca d'água.

Restrição por domínio
---------------------
A chave do projeto está restrita, no painel da CARTO, ao domínio
``terrace.virtual.ufc.br``. A CARTO valida essa restrição pelo cabeçalho
``Referer`` enviado pelo navegador, e devolve HTTP 403 (tiles cinza, sem
imagem) para requisições vindas de qualquer outra origem — inclusive
``localhost``. Por isso ``CARTO_API_KEY`` fica vazia em desenvolvimento local,
onde a alternativa OpenStreetMap é usada.

Como a verificação é feita sobre o ``Referer`` do navegador, não há como o
servidor Streamlit validar a chave por conta própria: uma requisição feita pelo
backend seria rejeitada mesmo com a chave correta. A configuração errada só
aparece no navegador do usuário.

Sobre o sigilo da chave
-----------------------
Uma API key de basemap é, por construção, visível no navegador do usuário — ela
viaja na URL de cada tile requisitado. Mesmo assim ela não é versionada no
repositório (que é público): em desenvolvimento fica em ``.env`` /
``.streamlit/secrets.toml``, ambos no ``.gitignore``, e em produção é injetada
como variável de ambiente do container.

A atribuição da CARTO e do OpenStreetMap é obrigatória e acompanha a camada em
todos os casos (https://carto.com/attributions).
"""

import os
from typing import Optional, Tuple

import folium
import streamlit as st

# Estilo usado pela maioria das páginas do dashboard.
ESTILO_PADRAO = "positron"

# Caminho de cada estilo raster dentro do CDN da CARTO.
_CARTO_ESTILOS = {
    "positron": "light_all",
    "positron_nolabels": "light_nolabels",
    "dark_matter": "dark_all",
    "voyager": "rastertiles/voyager",
}

_CARTO_HOST = "https://basemaps.cartocdn.com"

_CARTO_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
)

_OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_OSM_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    "contributors"
)

NOME_CAMADA_PADRAO = "Mapa base"

# Valor real da variável de ambiente, capturado antes de o Streamlit poder
# sobrescrevê-la com o conteúdo do secrets.toml. Ver a nota no topo do módulo.
_CARTO_API_KEY_DO_AMBIENTE = os.environ.get("CARTO_API_KEY")


def _normalizar(valor) -> Optional[str]:
    """Devolve a string sem espaços nas pontas, ou ``None`` se for vazia."""
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def get_carto_api_key() -> Optional[str]:
    """Devolve a API key da CARTO configurada, ou ``None`` se não houver.

    Consulta, nesta ordem: a variável de ambiente capturada na importação, a
    variável de ambiente no momento da chamada e, por fim, ``st.secrets``.
    Valores vazios ou só com espaços contam como ausência.

    A leitura de ``st.secrets`` é protegida porque o Streamlit levanta exceção
    quando não existe nenhum ``secrets.toml`` no ambiente.
    """
    chave = _normalizar(_CARTO_API_KEY_DO_AMBIENTE)
    if chave:
        return chave

    chave = _normalizar(os.environ.get("CARTO_API_KEY"))
    if chave:
        return chave

    try:
        bruto = st.secrets["CARTO_API_KEY"]
    except Exception:
        return None

    return _normalizar(bruto)


def basemap_tiles(estilo: str = ESTILO_PADRAO) -> Tuple[str, str]:
    """Devolve a tupla ``(url_do_tile, atribuicao)`` da camada base.

    Com API key configurada, devolve o estilo raster pedido da CARTO já com o
    parâmetro ``key``. Sem API key, devolve o OpenStreetMap como alternativa.
    """
    caminho = _CARTO_ESTILOS.get(estilo)
    if caminho is None:
        validos = ", ".join(sorted(_CARTO_ESTILOS))
        raise ValueError(f"Estilo de basemap desconhecido: {estilo!r}. Use um de: {validos}.")

    chave = get_carto_api_key()
    if not chave:
        return _OSM_TILES, _OSM_ATTR

    url = f"{_CARTO_HOST}/{caminho}/" + "{z}/{x}/{y}{r}.png" + f"?key={chave}"
    return url, _CARTO_ATTR


def adicionar_basemap(
    mapa: folium.Map,
    estilo: str = ESTILO_PADRAO,
    nome: str = NOME_CAMADA_PADRAO,
    control: bool = False,
    overlay: bool = False,
    **kwargs,
) -> folium.TileLayer:
    """Adiciona a camada base ao ``mapa`` e devolve a ``TileLayer`` criada.

    O ``nome`` é sempre explícito: se deixado a cargo do folium, o rótulo da
    camada no controle de camadas passaria a ser a própria URL do tile, expondo
    a API key na interface.
    """
    url, attr = basemap_tiles(estilo)
    camada = folium.TileLayer(
        tiles=url,
        attr=attr,
        name=nome,
        control=control,
        overlay=overlay,
        **kwargs,
    )
    camada.add_to(mapa)
    return camada


def criar_mapa(
    estilo: str = ESTILO_PADRAO,
    nome_camada: str = NOME_CAMADA_PADRAO,
    **kwargs,
) -> folium.Map:
    """Cria um ``folium.Map`` já com a camada base correta.

    Substitui o uso de ``folium.Map(tiles="cartodbpositron")``, que monta a URL
    dos tiles internamente e não permite acrescentar a API key. Qualquer
    ``tiles`` passado em ``kwargs`` é ignorado.
    """
    kwargs.pop("tiles", None)
    mapa = folium.Map(tiles=None, **kwargs)
    adicionar_basemap(mapa, estilo=estilo, nome=nome_camada)
    return mapa
