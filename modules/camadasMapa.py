# modules/camadasMapa.py
"""Camadas e controles de mapa compartilhados pelas páginas."""

import json
import math
from collections.abc import Iterable

import folium
from folium.plugins import FastMarkerCluster, Fullscreen, MiniMap
from shapely.geometry import shape
from streamlit_folium import st_folium

from modules.basemap import criarMapa
from modules.constantes import CENTRO_CEARA, COR_MUNICIPIO, CORES_ASSENTAMENTOS, NAO_DISPONIVEL, ZOOM_PADRAO
from modules.privacidade import escaparHtml, escaparPropriedades

CAMPOS_ASSENTAMENTO = [
    ("cd_sipra", "SIPRA:"),
    ("nome_assentamento", "Nome:"),
    ("nome_municipio_original", "Município:"),
    ("num_familias", "Famílias:"),
    ("forma_obtecao", "Forma de obtenção:"),
    ("area", "Área (ha):"),
    ("perimetro", "Perímetro:"),
]
ROTULOS_ASSENTAMENTO = {"Estadual": "Assentamentos Estaduais", "Federal": "Assentamentos Federais"}

_ICONE_FEDERAL = (
    '<div style="background-color:#FFFFFF;border:0.8px solid black;border-radius:50%;'
    'width:12px;height:12px;"></div>'
)
_ICONE_ESTADUAL = (
    '<svg width="20" height="20" viewBox="0 0 30 30">'
    '<polygon points="15,3 27,27 3,27" fill="#e5b636" stroke="black" stroke-width="0.5"/></svg>'
)
_CALLBACK_MARCADOR = """
function (linha) {
    var icones = __ICONES__;
    var icone = L.divIcon({html: icones[linha[2]], className: '', iconSize: [20, 20], iconAnchor: [10, 10]});
    var marcador = L.marker(new L.LatLng(linha[0], linha[1]), {icon: icone});
    marcador.bindTooltip(linha[3]);
    return marcador;
}
""".replace("__ICONES__", json.dumps({"Federal": _ICONE_FEDERAL, "Estadual": _ICONE_ESTADUAL}))


def formatarValor(valor):
    """Troca valores ausentes ou inválidos por "Não Disponível"."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return NAO_DISPONIVEL
    if isinstance(valor, str) and valor.strip().lower() in ("", "nan", "none", "null"):
        return NAO_DISPONIVEL
    return valor


def rotuloLegenda(cor: str, texto: str, forma: str = "quadrado") -> str:
    """HTML do nome de uma camada no controle de camadas, com a amostra de cor."""
    if forma == "circulo":
        amostra = f'<svg width="12" height="12"><circle cx="6" cy="6" r="6" fill="{cor}" /></svg>'
        return f"<span>{amostra} {texto}</span>"
    return (
        f'<span style="display:inline-block;width:12px;height:12px;background:{cor};'
        f'margin-right:6px;"></span>{texto}'
    )


def criarMapaBase(centro: list | None = None, zoom: int = ZOOM_PADRAO, **opcoes) -> folium.Map:
    """Mapa com a camada base do projeto, centrado no Ceará por padrão."""
    opcoes.setdefault("control_scale", True)
    opcoes.setdefault("prefer_canvas", True)
    return criarMapa(location=centro or CENTRO_CEARA, zoom_start=zoom, **opcoes)


def adicionarControles(mapa: folium.Map, controleCamadas: bool = True) -> None:
    """Controle de camadas, minimapa e botão de tela cheia."""
    if controleCamadas:
        folium.LayerControl(collapsed=False).add_to(mapa)
    MiniMap(toggle_display=True).add_to(mapa)
    Fullscreen().add_to(mapa)


def renderizarMapa(mapa: folium.Map, altura: int = 700, retornar: Iterable[str] = (), chave: str | None = None):
    """Exibe o mapa na largura do contêiner. Só devolve dados se ``retornar`` pedir."""
    return st_folium(mapa, height=altura, use_container_width=True, returned_objects=list(retornar), key=chave)


def adicionarCamadaMunicipios(
    mapa: folium.Map,
    geojson: dict | None,
    comTooltip: bool = True,
    nome: str = "Limites Municipais",
    estilo: dict | None = None,
) -> None:
    """Contorno dos municípios, sem preenchimento, desenhado uma única vez."""
    if not geojson or not geojson.get("features"):
        return
    tooltip = None
    if comTooltip:
        geojson = escaparPropriedades(geojson)
        tooltip = folium.GeoJsonTooltip(fields=["nome_municipio"], aliases=["Município:"], sticky=True)
    estiloFinal = {"fill": False, "color": COR_MUNICIPIO, "weight": 1, **(estilo or {})}
    folium.GeoJson(geojson, name=nome, style_function=lambda _: estiloFinal, tooltip=tooltip).add_to(mapa)


def _tipoAssentamento(feature: dict) -> str:
    return str(feature.get("properties", {}).get("tipo_assentamento") or "").strip().capitalize()


def _prepararAssentamento(feature: dict) -> dict:
    """Cópia da feição só com os campos exibidos, formatados e escapados."""
    origem = feature.get("properties") or {}
    propriedades = {campo: escaparHtml(formatarValor(origem.get(campo))) for campo, _ in CAMPOS_ASSENTAMENTO}
    propriedades["tipo_assentamento"] = escaparHtml(formatarValor(origem.get("tipo_assentamento")))
    return {"type": "Feature", "geometry": feature.get("geometry"), "properties": propriedades}


def _linhaMarcador(feature: dict, tipo: str) -> list | None:
    try:
        ponto = shape(feature["geometry"]).representative_point()
    except Exception:
        return None
    p = feature["properties"]
    tooltip = (
        f"<b>CD_SIPRA:</b> {p['cd_sipra']}<br><b>Tipo:</b> {p['tipo_assentamento']}<br>"
        f"<b>Assentamento:</b> {p['nome_assentamento']}<br><b>Município:</b> {p['nome_municipio_original']}<br>"
        f"<b>Famílias:</b> {p['num_familias']}<br><b>Forma de Obtenção:</b> {p['forma_obtecao']}<br>"
        f"<b>Área:</b> {p['area']} ha<br><b>Perímetro:</b> {p['perimetro']}"
    )
    return [round(ponto.y, 6), round(ponto.x, 6), tipo, tooltip]


def adicionarCamadasAssentamentos(
    mapa: folium.Map,
    geojson: dict | None,
    rotulos: dict | None = None,
    opacidade: float = 0.5,
    comMarcadores: bool = False,
) -> None:
    """Uma camada por tipo de assentamento presente nos dados.

    Tipos sem nenhuma feição não geram camada, o que evita o erro do folium ao
    montar o tooltip de um GeoJSON vazio. Com ``comMarcadores``, cada
    assentamento ganha um marcador agrupado em cluster, útil em zoom baixo.
    """
    if not geojson or not geojson.get("features"):
        return
    rotulos = rotulos or ROTULOS_ASSENTAMENTO
    campos = [c for c, _ in CAMPOS_ASSENTAMENTO]
    aliases = [a for _, a in CAMPOS_ASSENTAMENTO]
    for tipo, cor in CORES_ASSENTAMENTOS.items():
        feicoes = [_prepararAssentamento(f) for f in geojson["features"] if _tipoAssentamento(f) == tipo]
        if not feicoes:
            continue
        grupo = folium.FeatureGroup(name=rotuloLegenda(cor, rotulos.get(tipo, tipo)), overlay=True)
        folium.GeoJson(
            {"type": "FeatureCollection", "features": feicoes},
            style_function=lambda _, cor=cor: {"fillColor": cor, "color": "#000000", "weight": 0.5, "fillOpacity": opacidade},
            tooltip=folium.GeoJsonTooltip(fields=campos, aliases=aliases, sticky=True),
        ).add_to(grupo)
        if comMarcadores:
            linhas = [linha for f in feicoes if (linha := _linhaMarcador(f, tipo))]
            FastMarkerCluster(linhas, callback=_CALLBACK_MARCADOR, control=False).add_to(grupo)
        grupo.add_to(mapa)
