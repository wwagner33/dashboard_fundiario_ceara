# modules/mapa_escolas.py

import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MiniMap, Fullscreen, MarkerCluster
import requests
import math
from typing import Optional
from shapely.geometry import shape
from typing import Dict, List, Any, Optional
import os
import json
import pandas as pd

import jwt
from datetime import datetime, timedelta

# Configurações padrão
CENTRO_CEARA = [-5.2, -39.0]
ZOOM_PADRAO = 8
COR_ESCOLA = "#e74c3c"
CORES_ASSENTAMENTOS = {
    "Estadual": "#ff7f0e",  # Laranja
    "Federal": "#1f77b4",   # Azul
}
COR_MUNICIPIO = "#000000"  # cor da borda

# Dados das escolas do campo (hardcoded conforme solicitado)
ESCOLAS_DO_CAMPO = [
    {"crede": 2, "nome_municipio": "itapipoca", "assentamento": "Maceió", 
     "nome_escola": "EEM Maria Nazaré de Sousa", 
     "latitude": -3.129879627387401, "longitude": -39.52221661844289},
    {"crede": 3, "nome_municipio": "itarema", "assentamento": "Lagoa do Mineiro", 
     "nome_escola": "EEM Francisco Araújo Barros", 
     "latitude": -3.025238577636784, "longitude": -39.753315518444005},
    {"crede": 6, "nome_municipio": "santana_do_acarató", "assentamento": "Conceição Bonfim", 
     "nome_escola": "EEM José Fideles de Moura", 
     "latitude": -3.386111233883421, "longitude": -40.28083861844071},
    {"crede": 7, "nome_municipio": "caninde", "assentamento": "Santana da Cal", 
     "nome_escola": "EEM Filha da Luta Patativa do Assaré", 
     "latitude": -4.375812781017249, "longitude": -39.45617268959514},
    {"crede": 7, "nome_municipio": "caninde", "assentamento": "Logradouro", 
     "nome_escola": "EEM Antônio Tavares Alves", 
     "latitude": -4.490990998155495, "longitude": -39.2107603049365},
    {"crede": 7, "nome_municipio": "caninde", "assentamento": "Conceição Salitre", 
     "nome_escola": "EEM Javan Rodrigues de Sousa", 
     "latitude": -4.214808199746922, "longitude": -39.7451775049393},
    {"crede": 8, "nome_municipio": "ocara", "assentamento": "Antônio Conselheiro", 
     "nome_escola": "EEM Francisca Pinto dos Santos", 
     "latitude": -4.58715153922025, "longitude": -38.61961616445614},
    {"crede": 11, "nome_municipio": "jaguaretama", "assentamento": "Pedra e Cal", 
     "nome_escola": "EEM Pe. José Augusto Régis Alves", 
     "latitude": -5.468583905528393, "longitude": -38.75458134675905},
    {"crede": 12, "nome_municipio": "quixeramobim", "assentamento": "Canaã", 
     "nome_escola": "EEM Irmã Tereza Cristina", 
     "latitude": -5.367998686093881, "longitude": -39.319097133761986},
    {"crede": 12, "nome_municipio": "madalena", "assentamento": "25 de Maio", 
     "nome_escola": "EEM João dos Santos Oliveira", 
     "latitude": -5.027589544256683, "longitude": -39.531745949108526},
    {"crede": 13, "nome_municipio": "mons. Tabosa", "assentamento": "Santana", 
     "nome_escola": "EEM Florestan Fernandes", 
     "latitude": -3.750725526452395, "longitude": -38.55615224542324},
    {"crede": 13, "nome_municipio": "ipueiras", "assentamento": "Distrito de Balseiros", 
     "nome_escola": "EFA Padre Elfésio dos Santos", 
     "latitude": -4.680048368725458, "longitude": -40.80273330493446},
    {"crede": 14, "nome_municipio": "mombaça", "assentamento": "Salão Mombaça", 
     "nome_escola": "EEM Paulo Freire", 
     "latitude": -5.699846996424161, "longitude": -39.93511134725098}
]

# Configuração ajustável da API
JWT_SECRET = st.secrets["JWT_SECRET"]
JWT_ALGORITHM = "HS256"

def create_jwt_token():
    expiration = datetime.utcnow() + timedelta(minutes=30)
    payload = {
        "exp": expiration,
        "iat": datetime.utcnow(),
        "sub": "streamlit_app"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8000/api")
REQUEST_TIMEOUT = 120  # segundos

# --- Helpers ---

@st.cache_data(ttl=86400)
def _fetch_from_api(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Helper function com tratamento robusto de erros"""
    try:
        st.session_state.setdefault('api_calls', 0)
        st.session_state.api_calls += 1

        token = create_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(
            f"{DATA_SERVICE_URL}/{endpoint}",
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        # Verificação especial para evitar erro com endpoint /version
        if endpoint == "version":
            if response.status_code == 404:
                return {'data_version': '1.0.0-default'}  # Versão padrão
            response.raise_for_status()
            return response.json()
        else:
            response.raise_for_status()
            return response.json()
            
    except requests.exceptions.RequestException as e:
        if endpoint == "version":
            return {'data_version': '1.0.0-fallback'}  # Versão de fallback
        
        # Fallback para dados locais se disponível
        if os.path.exists(f"backup/{endpoint}.json"):
            with open(f"backup/{endpoint}.json") as f:
                return json.load(f)
        st.error(f"Erro ao acessar endpoint {endpoint}: {str(e)}")
        raise

@st.cache_data(ttl=3600)
def carregar_assentamentos(municipio: str = "todos") -> Optional[dict]:
    return _fetch_from_api("geojson_assentamentos", {'municipio': municipio})

@st.cache_data(ttl=3600)
def carregar_municipios(municipio: str = "todos") -> Optional[dict]:
    return _fetch_from_api("geojson_muni", {'municipio': municipio})

@st.cache_data(ttl=3600)
def obter_municipios_com_escolas() -> list:
    """Obtém a lista de municípios que possuem escolas do campo"""
    municipios = list(set([escola["nome_municipio"] for escola in ESCOLAS_DO_CAMPO]))
    municipios.sort()
    return ["Todos"] + municipios

# --- Formatação ---
def formatar_valor(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "Não Disponível"
    if isinstance(valor, str) and valor.strip().lower() in ["", "nan", "none", "null"]:
        return "Não Disponível"
    return valor

# --- Camadas do mapa ---
def criar_mapa_base() -> folium.Map:
    return folium.Map(
        location=CENTRO_CEARA,
        zoom_start=ZOOM_PADRAO,
        tiles="cartodbpositron", 
        control_scale=True,
        prefer_canvas=True
    )

def adicionar_camadas_assentamentos(mapa: folium.Map, geojson_data: dict):
    if not geojson_data or not geojson_data.get("features"):
        return

    # Separar assentamentos por tipo
    assentamentos_estaduais = {
        "type": "FeatureCollection",
        "features": [feat for feat in geojson_data['features'] 
                    if feat.get('properties', {}).get('tipo_assentamento') == 'estadual']
    }
    
    assentamentos_federais = {
        "type": "FeatureCollection",
        "features": [feat for feat in geojson_data['features'] 
                    if feat.get('properties', {}).get('tipo_assentamento') == 'federal']
    }

    # Camada Assentamentos Estaduais
    nome_estadual = (
        f'<span style="display:inline-block;'
        f'width:12px;height:12px;background:{CORES_ASSENTAMENTOS["Estadual"]};'
        f'margin-right:6px;"></span>Assentamentos Estaduais'
    )
    fg_estadual = folium.FeatureGroup(name=nome_estadual, overlay=True)

    folium.GeoJson(
        assentamentos_estaduais,
        style_function=lambda ft: {
            "fillColor": CORES_ASSENTAMENTOS["Estadual"],
            "color": "#000000",
            "weight": 0.5,
            "fillOpacity": 0.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                'cd_sipra', 'nome_assentamento', 'nome_municipio_original',
                'num_familias', 'forma_obtecao', 'area', 'perimetro'
            ],
            aliases=[
                'SIPRA:', 'Nome:', 'Município:',
                'Famílias:', 'Forma de Obtenção:', 'Área (ha):', 'Perímetro (m):'
            ],
            sticky=True
        )
    ).add_to(fg_estadual)
    fg_estadual.add_to(mapa)

    # Camada Assentamentos Federais
    nome_federal = (
        f'<span style="display:inline-block;'
        f'width:12px;height:12px;background:{CORES_ASSENTAMENTOS["Federal"]};'
        f'margin-right:6px;"></span>Assentamentos Federais'
    )
    fg_federal = folium.FeatureGroup(name=nome_federal, overlay=True)

    folium.GeoJson(
        assentamentos_federais,
        style_function=lambda ft: {
            "fillColor": CORES_ASSENTAMENTOS["Federal"],
            "color": "#000000",
            "weight": 0.5,
            "fillOpacity": 0.5
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                'cd_sipra', 'nome_assentamento', 'nome_municipio_original',
                'num_familias', 'forma_obtecao', 'area', 'perimetro'
            ],
            aliases=[
                'SIPRA:', 'Nome:', 'Município:',
                'Famílias:', 'Forma de Obtenção:', 'Área (ha):', 'Perímetro (m):'
            ],
            sticky=True
        )
    ).add_to(fg_federal)
    fg_federal.add_to(mapa)

def adicionar_camada_escolas(mapa: folium.Map, escolas_data: list):
    if not escolas_data:
        st.warning("Nenhuma escola do campo para mostrar 😕")
        return

    nome_fg = (
        f'<span style="display:inline-block;'
        f'width:12px;height:12px;background:{COR_ESCOLA};'
        f'margin-right:6px;"></span>Escolas do Campo'
    )
    fg = folium.FeatureGroup(name=nome_fg, overlay=True)

    # Cluster de markers para escolas
    cluster = MarkerCluster().add_to(fg)
    
    for escola in escolas_data:
        tooltip = (
            f"<b>CREDE: {escola['crede']}</b><br>"
            f"<b>Município: {escola['nome_municipio']}</b><br>"
            f"<b>Assentamento: {escola['assentamento']}</b><br>"
            f"<b>Escola: {escola['nome_escola']}</b>"
        )
        
        folium.Marker(
            [escola['latitude'], escola['longitude']],
            tooltip=tooltip,
            popup=folium.Popup(tooltip, max_width=300),
            icon=folium.Icon(prefix='fa', icon='school', color='red')
        ).add_to(cluster)

    fg.add_to(mapa)

def adicionar_camada_municipios(mapa: folium.Map, geojson_data: dict, with_tooltip: bool = True):
    if not geojson_data or not geojson_data.get("features"):
        return

    fg = folium.FeatureGroup(name="Limites Municipais", overlay=True)
    if with_tooltip:
        folium.GeoJson(
            geojson_data,
            style_function=lambda ft: {
                "fill": False,          
                "color": COR_MUNICIPIO,
                "weight": 1
            },
            simplify_tolerance=0.001,
            tooltip=folium.GeoJsonTooltip(
                fields=['nome_municipio'],
                aliases=['Município:'],
                sticky=True
            )
        ).add_to(fg)
    else:
        folium.GeoJson(
           geojson_data,
            style_function=lambda ft: {
                "fill": False,          
                "color": COR_MUNICIPIO,
                "weight": 1
            },
            simplify_tolerance=0.001
        ).add_to(fg)
    fg.add_to(mapa)

def obter_estatisticas_escolas(escolas_data: list):
    if not escolas_data:
        return {"total": 0}
    
    # Contar escolas por CREDE
    credes = {}
    for escola in escolas_data:
        credes[escola['crede']] = credes.get(escola['crede'], 0) + 1
    
    return {
        "total": len(escolas_data),
        "por_crede": credes
    }

def render_view_escolas_map():
    muni_list = obter_municipios_com_escolas()
    col1, col2 = st.columns([7, 3])

    with col2:
        st.html("""
                <p class="paragrafo-com-icone" style="padding-bottom: 0px">
                    <span class="icone-svg"></span> 
                    Este mapa exibe as escolas do campo no Ceará, permitindo filtrar
                    por município e visualizar informações detalhadas como CREDE,
                    assentamento e nome da escola.
                </p>
                """)
        st.markdown(f"### Filtros")
        st.html("""<span style='color: #000000 !important'>Do Estado do Ceará </span>
                """)
        sel = st.selectbox("Município", muni_list, index=0)
        
        # Filtrar escolas por município selecionado
        if sel == "Todos":
            escolas_filtradas = ESCOLAS_DO_CAMPO
        else:
            escolas_filtradas = [e for e in ESCOLAS_DO_CAMPO if e["nome_municipio"] == sel.lower()]
        
        stats = obter_estatisticas_escolas(escolas_filtradas)
        
        st.html("""
                <p class="paragrafo-com-icone" style="padding-bottom: 0px">
                    <span class="icone-svg"></span> 
                    Inclui também camadas com limites municipais e assentamentos rurais
                    para contexto geográfico, oferecendo uma visão integrada da educação
                    no campo.
                </p>
                """)
        
        st.metric("Escolas do Campo", stats["total"])
        
        # Mostrar distribuição por CREDE
        st.markdown("**Distribuição por CREDE:**")
        for cred, count in stats["por_crede"].items():
            st.markdown(f"- CREDE {cred}: {count} escola(s)")

    with col1:  
        if "geo_muni" not in st.session_state:
            st.session_state.geo_muni = carregar_municipios("todos")
        if "geo_assent" not in st.session_state:
            st.session_state.geo_assent = carregar_assentamentos("todos")

        mapa = criar_mapa_base()
        adicionar_camada_municipios(mapa, st.session_state.geo_muni)
        adicionar_camadas_assentamentos(mapa, st.session_state.geo_assent)
        adicionar_camada_escolas(mapa, escolas_filtradas)

        folium.LayerControl(collapsed=False).add_to(mapa)
        MiniMap(toggle_display=True).add_to(mapa)
        Fullscreen().add_to(mapa)
        st_folium(mapa, width=1000, height=700, returned_objects=[], use_container_width=True)