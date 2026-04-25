PATTERNS = [
    {
        "intent": "time",
        "patterns": [
            r'\b(quelle heure (est[- ]il|il est)|il est quelle heure|tu as l\'heure|heure actuelle)\b'
        ]
    },
    {
        "intent": "day",
        "patterns": [
            r'\b(quel jour sommes[- ]nous|on est quel jour|c\'est quel jour)\b'
        ]
    },
    {
        "intent": "date",
        "patterns": [
            r'\b(quelle date|on est le combien|date d\'aujourd\'hui)\b'
        ]
    },
    {
        "intent": "year",
        "patterns": [
            r'\b(quelle année|année actuelle)\b'
        ]
    },
    {
        "intent": "duration",
        "patterns": [
            r'\b(dans combien de temps|combien de temps avant|il reste combien de temps)\b'
        ]
    },
    {
        "intent": "math",
        "patterns": [
            r'\b(\d+\s*[\+\-\*\/x]\s*\d+)\b'
        ]
    },
    {
        "intent": "percentage",
        "patterns": [
            r'\b(\d+\s*% ?de\s*\d+)\b'
        ]
    },
    {
        "intent": "coin",
        "patterns": [
            r'\b(pile ou face|lance une pièce)\b'
        ]
    },
    {
        "intent": "random",
        "patterns": [
            r'\b(nombre aléatoire|au hasard|choisis un nombre)\b'
        ]
    }
]