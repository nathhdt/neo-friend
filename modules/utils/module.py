import re
import random

from core.module_base import ModuleBase
from datetime import datetime
from langchain_core.tools import tool
from typing import Dict, Any, Optional, List
from utils.logging import step_start, step_ok, step_error

from .call_patterns import PATTERNS


class UtilsModule(ModuleBase):

    def get_patterns(self) -> Dict[str, list]:
        return {"patterns": PATTERNS, "priority": 90}

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
            """Effectue un calcul mathématique. Accepte des expressions comme '2+2', '15*3', '100/4'. Utilise cet outil quand l'utilisateur demande un calcul ou un pourcentage.
            
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

    async def handle(self, user_input: str, context: Dict[str, Any]) -> Optional[str]:
        intent = context.get("intent")
        text = user_input.lower()

        if intent == "time":
            return self._get_time()
        if intent == "day":
            return self._get_day()
        if intent == "date":
            return self._get_date()
        if intent == "year":
            return self._get_year()
        if intent == "duration":
            return self._duration(text)
        if intent == "math":
            return self._calculate(text)
        if intent == "percentage":
            return self._percentage(text)
        if intent == "coin":
            return self._coin_flip()
        if intent == "random":
            return self._random_number()
        return None

    def _get_time(self) -> str:
        now = datetime.now()
        return f"Il est {now.hour} heures {now.minute}."

    def _get_day(self) -> str:
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.now()
        return f"Aujourd'hui, on est {days[now.weekday()]}."

    def _get_date(self) -> str:
        now = datetime.now()
        return f"On est le {now.day} {self._month(now.month)} {now.year}."

    def _get_year(self) -> str:
        return f"On est en {datetime.now().year}."

    def _duration(self, text: str) -> str:
        now = datetime.now()
        if "juin" in text:
            target = datetime(now.year, 6, 1)
            delta = target - now
            return f"Il reste {delta.days} jours."
        return "Je n'ai pas compris la durée."

    def _month(self, m: int) -> str:
        months = [
            "janvier", "février", "mars", "avril",
            "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"
        ]
        return months[m - 1]

    def _calculate(self, text: str) -> str:
        try:
            expr = re.findall(r'[\d\.\+\-\*\/\(\)\s]+', text)[0]
            result = eval(expr)
            return f"Ça fait {result}."
        except Exception:
            return "Je n'ai pas réussi à calculer."

    def _percentage(self, text: str) -> str:
        try:
            match = re.search(r'(\d+)\s*%\s*de\s*(\d+)', text)
            if match:
                p = float(match.group(1))
                n = float(match.group(2))
                result = (p / 100) * n
                return f"{p}% de {n}, ça fait {result}."
        except Exception:
            pass
        return "Je n'ai pas compris le pourcentage."

    def _coin_flip(self) -> str:
        return random.choice(["Pile.", "Face."])

    def _random_number(self) -> str:
        return f"Je choisis {random.randint(0, 100)}."