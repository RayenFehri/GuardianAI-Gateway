"""
conftest.py — permet à pytest de trouver les modules du projet (classifier, oui_lookup...)
même si les tests sont dans un sous-dossier tests/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
