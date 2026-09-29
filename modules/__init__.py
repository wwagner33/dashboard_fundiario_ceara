# modules/__init__.py
"""Pacote do dashboard fundiário do Ceará.

``basemap`` e ``config`` são importados primeiro: os dois capturam variáveis de
ambiente (``CARTO_API_KEY`` e ``JWT_SECRET``) antes que qualquer leitura de
``st.secrets`` faça o Streamlit sobrescrever ``os.environ``.
"""

from . import basemap, config  # noqa: F401

__version__ = "1.1.1"
