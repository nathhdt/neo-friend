import json
import math
import urllib.request
import urllib.parse

from core.module_base import ModuleBase
from datetime import datetime, timedelta
from langchain_core.tools import tool
from typing import List, Tuple
from utils.logging import step_ok, technical_log


WMO_CODES = {
    0:  "ciel dégagé",
    1:  "peu nuageux", 2: "partiellement nuageux", 3: "couvert",
    45: "brouillard", 48: "brouillard givrant",
    51: "bruine légère", 53: "bruine modérée", 55: "bruine dense",
    61: "pluie légère", 63: "pluie modérée", 65: "pluie forte",
    71: "neige légère", 73: "neige modérée", 75: "neige forte",
    77: "grains de neige",
    80: "averses légères", 81: "averses modérées", 82: "averses violentes",
    85: "averses de neige légères", 86: "averses de neige fortes",
    95: "orage", 96: "orage avec grêle", 99: "orage avec grêle forte",
}


def _fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


def _geolocate_ip() -> Tuple[float, float, str]:
    """Retourne (lat, lon, city) depuis l'IP publique."""
    data = _fetch("http://ip-api.com/json/?fields=lat,lon,city")
    return data["lat"], data["lon"], data.get("city", "ta position")


def _geocode(location: str) -> Tuple[float, float, str]:
    """Convertit un nom de lieu en (lat, lon, display_name)."""
    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({"name": location, "count": 1, "language": "fr"})
    )
    data = _fetch(url)
    results = data.get("results")
    if not results:
        raise ValueError(f"Lieu introuvable : {location}")
    r = results[0]
    name = r.get("name", location)
    country = r.get("country", "")
    display = f"{name}, {country}" if country else name
    return r["latitude"], r["longitude"], display


def _rain_label(mm: float) -> str:
    if mm < 1:
        return "pas de pluie"
    if mm < 5:
        return "pluie légère"
    if mm < 20:
        return "pluie modérée"
    return "pluie importante"


def _wind_label(kmh: float) -> str:
    if kmh < 20:
        return "vent faible"
    if kmh < 50:
        return "vent modéré"
    return "vent fort"


def _fetch_weather(lat: float, lon: float, days: int) -> dict:
    """Appelle Open-Meteo et retourne les données brutes."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join([
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max",
        ]),
        "timezone": "auto",
        "forecast_days": min(days, 7),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    return _fetch(url)


def _format_day(date_str: str, code: int, t_max: float, t_min: float,
                rain: float, wind: float) -> str:
    """Formate une journée en texte naturel."""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if date == today:
        day_label = "Aujourd'hui"
    elif date == tomorrow:
        day_label = "Demain"
    else:
        days_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        months_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
                     "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        day_label = f"{days_fr[date.weekday()].capitalize()} {date.day} {months_fr[date.month - 1]}"

    desc = WMO_CODES.get(code, "temps variable")
    t_max_r = math.ceil(t_max) if t_max % 1 >= 0.5 else math.floor(t_max)
    t_min_r = math.ceil(t_min) if t_min % 1 >= 0.5 else math.floor(t_min)

    return (
        f"{day_label} : {desc}, {t_min_r}–{t_max_r}°C, "
        f"{_rain_label(rain)}, {_wind_label(wind)}"
    )


class WeatherModule(ModuleBase):

    def on_load(self):
        step_ok("weather", "ready")

    def get_tools(self) -> List:

        @tool
        def get_weather(location: str = "", days: int = 1) -> str:
            """Donne la météo pour un lieu et un nombre de jours. Utilise cet outil quand l'utilisateur demande le temps qu'il fait, s'il va pleuvoir, la température, le soleil, ou toute question météo.

            Si le lieu n'est pas précisé, détecte automatiquement la position de l'utilisateur.
            Si une ville ou un pays est mentionné dans la question, utilise ce lieu.

            Args:
                location: ville ou lieu (ex: "Londres", "Tokyo"). Laisser vide pour position automatique.
                days: nombre de jours de prévision (1 = aujourd'hui, 2 = aujourd'hui + demain, etc., max 7)
            """
            try:
                if location.strip():
                    lat, lon, place = _geocode(location.strip())
                else:
                    lat, lon, place = _geolocate_ip()

                data = _fetch_weather(lat, lon, days)
                daily = data["daily"]

                dates   = daily["time"]
                codes   = daily["weathercode"]
                t_maxes = daily["temperature_2m_max"]
                t_mines = daily["temperature_2m_min"]
                rains   = daily["precipitation_sum"]
                winds   = daily["windspeed_10m_max"]

                lines = [f"Météo à {place} :"]
                for i in range(min(days, len(dates))):
                    lines.append(_format_day(
                        dates[i], codes[i],
                        t_maxes[i], t_mines[i],
                        rains[i], winds[i]
                    ))

                return "\n".join(lines)

            except Exception as e:
                technical_log("weather", f"error: {e}")
                return f"Impossible de récupérer la météo : {e}"

        return [get_weather]