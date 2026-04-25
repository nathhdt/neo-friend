import re
import random
from datetime import datetime
from typing import Dict, Any, Optional

from core.module_base import ModuleBase
from utils.logging import technical_log


from .call_patterns import PATTERNS


class UtilsModule(ModuleBase):

    def get_patterns(self) -> Dict[str, list]:
        return {"patterns": PATTERNS, "priority": 90}

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
        days = [
            "lundi", "mardi", "mercredi",
            "jeudi", "vendredi", "samedi", "dimanche"
        ]
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
        except:
            return "Je n'ai pas réussi à calculer."

    def _percentage(self, text: str) -> str:
        try:
            match = re.search(r'(\d+)\s*%\s*de\s*(\d+)', text)
            if match:
                p = float(match.group(1))
                n = float(match.group(2))
                result = (p / 100) * n
                return f"{p}% de {n}, ça fait {result}."
        except:
            pass
        return "Je n'ai pas compris le pourcentage."

    def _coin_flip(self) -> str:
        return random.choice(["Pile.", "Face."])

    def _random_number(self) -> str:
        n = random.randint(0, 100)
        return f"Je choisis {n}."

    def on_load(self):
        technical_log("utils", "module loaded")