import re
import random

from core.module_base import ModuleBase
from datetime import datetime
from langchain_core.tools import tool
from typing import List


class UtilsModule(ModuleBase):

    def get_tools(self) -> List:
        """Expose les utilitaires comme LangChain Tools"""

        @tool
        def get_current_time() -> str:
            """Donne l'heure actuelle. Utilise cet outil quand l'utilisateur demande l'heure."""
            now = datetime.now()
            return f"Il est {now.hour} heures {now.minute:02d}."

        @tool
        def get_current_date() -> str:
            """Donne la date complète du jour (jour de la semaine, numéro, mois, année). Utilise cet outil quand l'utilisateur demande la date, le jour, ou l'année."""
            days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            months = [
                "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"
            ]
            now = datetime.now()
            return f"{days[now.weekday()]} {now.day} {months[now.month - 1]} {now.year}"

        @tool
        def calculate(expression: str) -> str:
            """Effectue un calcul mathématique. Accepte des expressions comme '2+2', '15*3', '100/4', ou '15% de 200'. Utilise cet outil quand l'utilisateur demande un calcul ou un pourcentage.

            Args:
                expression: Expression mathématique à évaluer (ex: '2+2', '15% de 200')
            """
            try:
                pct_match = re.search(r'(\d+)\s*%\s*de\s*(\d+)', expression)
                if pct_match:
                    p = float(pct_match.group(1))
                    n = float(pct_match.group(2))
                    result = (p / 100) * n
                    return f"{p}% de {n} = {result}"

                clean = re.sub(r'[^\d\.\+\-\*\/\(\)\s]', '', expression)
                result = eval(clean)
                return f"{expression} = {result}"
            except Exception:
                return f"Impossible de calculer : {expression}"

        @tool
        def coin_flip() -> str:
            """Lance une pièce et retourne pile ou face. Utilise cet outil quand l'utilisateur demande un tirage à pile ou face."""
            return random.choice(["Pile.", "Face."])

        @tool
        def random_number() -> str:
            """Génère un nombre aléatoire entre 0 et 100. Utilise cet outil quand l'utilisateur demande un nombre au hasard."""
            return f"{random.randint(0, 100)}"

        return [get_current_time, get_current_date, calculate, coin_flip, random_number]