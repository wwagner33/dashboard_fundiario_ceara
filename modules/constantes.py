# modules/constantes.py
"""Constantes compartilhadas pelas páginas de mapa."""

CENTRO_CEARA = [-5.2, -39.0]
ZOOM_PADRAO = 8

# SIRGAS 2000 / UTM 24S: projeção métrica que cobre o Ceará. Usada para
# calcular centróides sem a distorção das coordenadas geográficas.
CRS_METRICO = "EPSG:31984"
CRS_GEOGRAFICO = "EPSG:4326"

COR_MUNICIPIO = "#000000"
COR_RESERVATORIO = "#006994"
COR_ESCOLA = "#e74c3c"
CORES_ASSENTAMENTOS = {
    "Estadual": "#ff7f0e",
    "Federal": "#1f77b4",
}

# Tolerância de simplificação pedida ao miniserver para os assentamentos,
# em graus (cerca de 100 m no Ceará).
TOLERANCIA_ASSENTAMENTOS = 0.001

NAO_DISPONIVEL = "Não Disponível"
