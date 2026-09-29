"""Benchmark das páginas do dashboard com dados sintéticos em volume realista.

Não faz parte da suíte do pytest (o nome não começa com ``test_``). Rode com:

    .venv/bin/python -m tests.benchPaginas [saida.json]

Para cada página mede, com a API do miniserver simulada:

- ``frioS``: tempo da primeira execução, com os caches do Streamlit vazios;
- ``quenteS``: tempo de uma nova execução na mesma sessão, que é o custo de
  cada interação do usuário;
- ``requisicoes``: chamadas HTTP feitas na execução fria;
- ``htmlMapaKb``: tamanho do HTML gerado pelo folium para o mapa da página.
"""
import json
import math
import os
import random
import re
import sys
import time

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("JWT_SECRET", "segredo-do-benchmark-com-mais-de-32-bytes-012345")

import requests_mock  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

SEMENTE = 42
NUM_REGIOES = 14
NUM_MUNICIPIOS = 184
NUM_LOTES = 30000
NUM_PROPRIETARIOS = 9000
NUM_ASSENTAMENTOS = 600
NUM_RESERVATORIOS = 150

# Chave de sessão e identificadores de página. Ajuste aqui se a navegação mudar.
CHAVE_PAGINA = os.environ.get("BENCH_CHAVE_PAGINA", "current_page")
PAGINAS = json.loads(os.environ.get("BENCH_PAGINAS", "null")) or {
    "Início": "Inicio",
    "Gráficos": "Gráficos",
    "Predominância": "Mapa de Predominância",
    "Malha Fundiária": "Mapa da Malha Fundiária",
    "Concentração (Gini)": "Mapa de Concentração Fundiária",
    "Assentamentos": "Mapa de Assentamento",
    "Hidrográfico": "Mapa Hidrografico",
    "Escolas do Campo": "Mapa Escolas do Campo",
    "Sobre": "Sobre",
}


def _circulo(lon, lat, raio, vertices):
    pontos = [
        [round(lon + raio * math.cos(2 * math.pi * k / vertices), 6),
         round(lat + raio * math.sin(2 * math.pi * k / vertices), 6)]
        for k in range(vertices)
    ]
    return {"type": "Polygon", "coordinates": [pontos + [pontos[0]]]}


def _categoria(area, mf):
    if area < mf:
        return "Pequena Propriedade < 1 MF"
    if area <= 4 * mf:
        return "Pequena Propriedade"
    return "Média Propriedade" if area <= 15 * mf else "Grande Propriedade"


def gerarDados():
    rnd = random.Random(SEMENTE)
    regioes = [f"Região {i:02d}" for i in range(1, NUM_REGIOES + 1)]
    municipios = []
    for i in range(NUM_MUNICIPIOS):
        lin, col = divmod(i, 14)
        municipios.append({
            "nome": f"municipio_{i:03d}",
            "original": f"Município {i:03d}",
            "regiao": regioes[i % NUM_REGIOES],
            "lon": -41.3 + col * 0.29,
            "lat": -2.9 - lin * 0.36,
            "mf": rnd.choice([10, 20, 30, 40, 50, 55, 60, 70, 80, 90]),
        })
    limites = [
        {"type": "Feature", "properties": {"nome_municipio": m["nome"]},
         "geometry": _circulo(m["lon"], m["lat"], 0.13, 80)}
        for m in municipios
    ]
    proprietarios = [f"Proprietário {i:05d}" for i in range(NUM_PROPRIETARIOS)]
    lotes = []
    for i in range(NUM_LOTES):
        m = rnd.choice(municipios)
        area = round(rnd.lognormvariate(3, 1.4), 2)
        lotes.append({
            "numero_lote": str(i), "numero_incra": f"{i:013d}", "situacao_juridica": "Titulado",
            "modulo_fiscal": float(m["mf"]), "area": area,
            "nome_municipio": m["nome"], "nome_proprietario": rnd.choice(proprietarios),
            "nome_distrito": "Sede", "numero_titulo": str(i), "regiao_administrativa": m["regiao"],
            "categoria": _categoria(area, m["mf"]), "nome_municipio_original": m["original"], "imovel": f"Sítio {i}",
            "data_criacao_lote": "2020-01-01",
            "_lon": m["lon"] + rnd.uniform(-0.1, 0.1), "_lat": m["lat"] + rnd.uniform(-0.1, 0.1),
        })
    assentamentos = []
    for i in range(NUM_ASSENTAMENTOS):
        m = rnd.choice(municipios)
        assentamentos.append({"type": "Feature", "properties": {
            "cd_sipra": f"CE{i:04d}", "nome_municipio": m["nome"], "nome_assentamento": f"Assentamento {i}",
            "nome_municipio_original": m["original"], "area": round(rnd.uniform(50, 3000), 2),
            "perimetro": round(rnd.uniform(1, 40), 2), "forma_obtecao": "Desapropriação",
            "tipo_assentamento": "estadual" if i % 3 else "federal", "num_familias": rnd.randint(5, 200)},
            "geometry": _circulo(m["lon"] + rnd.uniform(-0.1, 0.1), m["lat"] + rnd.uniform(-0.1, 0.1), 0.02, 40)})
    reservatorios = []
    for i in range(NUM_RESERVATORIOS):
        m = rnd.choice(municipios)
        reservatorios.append({"type": "Feature", "properties": {
            "id_sagreh": str(i), "nome": f"Açude {i}", "proprietario": "Estado", "gerencia": "COGERH",
            "reg_hidrog": "Bacia 1", "nome_municipio": m["nome"], "nome_municipio_original": m["original"],
            "ini_monito": "2000", "ano_constr": "1990", "o_barrad": "Sim", "ac_jusante": None, "id_ac_jus": None,
            "area_ha": round(rnd.uniform(10, 5000), 2), "capacid_m3": round(rnd.uniform(1e5, 1e9), 2),
            "cot_vert_m": None, "lg_vert_m": None, "cot_td_m": None, "tipo_verte": None, "ri": "Rio Teste"},
            "geometry": _circulo(m["lon"], m["lat"], 0.03, 30)})
    return regioes, municipios, limites, lotes, assentamentos, reservatorios


def criarResponder(dados):
    regioes, municipios, limites, lotes, assentamentos, reservatorios = dados
    porRegiao, porMunicipio = {}, {}
    for lote in lotes:
        porRegiao.setdefault(lote["regiao_administrativa"].lower(), []).append(lote)
        porMunicipio.setdefault(lote["nome_municipio"].lower(), []).append(lote)

    def semPrivados(lote):
        return {k: v for k, v in lote.items() if not k.startswith("_")}

    def comoGeojson(lista):
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": semPrivados(lote),
             "geometry": _circulo(lote["_lon"], lote["_lat"], 0.004, 5)} for lote in lista]}

    def responder(request, context):
        caminho = request.path.rstrip("/")
        if caminho.startswith("/api"):
            caminho = caminho[len("/api"):]
        qs = {k: v[0] for k, v in request.qs.items()}
        context.status_code = 200
        if caminho == "/regioes":
            return {"regioes": regioes}
        if caminho == "/municipios":
            return {"municipios": sorted(m["nome"] for m in municipios if m["regiao"].lower() == qs.get("regiao", ""))}
        if caminho == "/municipios_todos":
            return {"municipios": [m["nome"] for m in municipios]}
        if caminho == "/geojson_muni":
            alvo = qs.get("municipio", "todos")
            feats = limites if alvo == "todos" else [f for f in limites if f["properties"]["nome_municipio"] == alvo]
            return {"type": "FeatureCollection", "features": feats}
        if caminho == "/dados_fundiarios":
            lista = porRegiao.get(qs.get("regiao", ""), []) or porMunicipio.get(qs.get("municipio", ""), [])
            return [semPrivados(l) for l in lista]
        if caminho == "/geojson":
            lista = porRegiao.get(qs.get("regiao", ""), []) or porMunicipio.get(qs.get("municipio", ""), [])
            return comoGeojson(lista)
        if caminho == "/geojson_assentamentos":
            alvo = qs.get("municipio", "todos")
            feats = assentamentos if alvo == "todos" else [f for f in assentamentos if f["properties"]["nome_municipio"] == alvo]
            return {"type": "FeatureCollection", "features": feats}
        if caminho == "/assentamentos_municipios":
            return {"municipios": sorted({f["properties"]["nome_municipio"] for f in assentamentos})}
        if caminho == "/geojson_reservatorios":
            alvo = qs.get("municipio", "todos")
            feats = reservatorios if alvo == "todos" else [f for f in reservatorios if f["properties"]["nome_municipio"] == alvo]
            return {"type": "FeatureCollection", "features": feats}
        if caminho == "/reservatorios_municipios":
            return {"municipios": sorted({f["properties"]["nome_municipio"] for f in reservatorios})}
        context.status_code = 404
        return {"detail": "não encontrado"}

    return responder


TAMANHOS_MAPA = []


def _stFoliumFalso(fig, *args, **kwargs):
    TAMANHOS_MAPA.append(len(fig.get_root().render().encode("utf-8")))
    return {}


def _substituirStFolium():
    import streamlit_folium
    streamlit_folium.st_folium = _stFoliumFalso
    for nome, modulo in list(sys.modules.items()):
        if nome.startswith("modules") and hasattr(modulo, "st_folium"):
            modulo.st_folium = _stFoliumFalso


def medirPagina(chave):
    st.cache_data.clear()
    st.cache_resource.clear()
    TAMANHOS_MAPA.clear()
    at = AppTest.from_file("app.py", default_timeout=300)
    at.session_state[CHAVE_PAGINA] = chave
    inicio = time.perf_counter()
    at.run()
    frio = time.perf_counter() - inicio
    erros = [str(e.value).splitlines()[0] for e in at.exception]
    html = max(TAMANHOS_MAPA) if TAMANHOS_MAPA else 0
    inicio = time.perf_counter()
    at.run()
    quente = time.perf_counter() - inicio
    return {"frioS": round(frio, 2), "quenteS": round(quente, 2), "htmlMapaKb": round(html / 1024), "erros": erros}


def main():
    import modules  # noqa: F401  (carrega os módulos antes de trocar o st_folium)
    _substituirStFolium()
    responder = criarResponder(gerarDados())
    resultados = {}
    with requests_mock.Mocker() as mock:
        mock.get(re.compile(r"^http://localhost:8000"), json=responder)
        for rotulo, chave in PAGINAS.items():
            antes = mock.call_count
            r = medirPagina(chave)
            r["requisicoes"] = mock.call_count - antes
            resultados[rotulo] = r
            print(f"{rotulo:22s} frio {r['frioS']:7.2f}s  quente {r['quenteS']:6.2f}s  "
                  f"req {r['requisicoes']:4d}  mapa {r['htmlMapaKb']:6d} KB  {r['erros'] or ''}", flush=True)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
