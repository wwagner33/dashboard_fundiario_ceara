# modules/__init__.py

"""
Exposição unificada de todos os componentes do pacote `modules`,
para imports mais limpos em app.py.
"""

from .data_loader import (
    load_csv_data as load_data,
    load_municipios,
    validate_data
)
from .grafico_interativo import (
    filtrar_dados,
    classificar_propriedades,
    plot_barras,
    plot_pizza,
    compute_stats_df
)
from .mapa_contextual import (
    preparar_dados,
    criar_choropleth_contextual
)
from .mapa_interativo import (
    preprocessar_tudo,
    criar_mapa_com_camadas
)
