PATTERNS = [
    {
        "intent": "count",
        "patterns": [
            r'\b(combien|nombre|quantite) (de |d\' |)mails?\b',
            r'\b(j\'ai|ai-je|jai) (combien de |des |)mails?\b',
            r'\best-ce que (j\'ai|tu as|jai) (des |)mails?\b',
            r'\b(y a-t-il|il y a|ya) (des |)mails?\b',
            r'\b(nouveau|nouveaux|new) mails?\b',
            r'\b(j\'ai recu|recu|jai recu) (des |un |)mails?\b',
        ]
    },
    {
        "intent": "list",
        "patterns": [
            r'\b(titre|titres|sujet|sujets) (des |de mes |)mails?\b',
            r'\b(quel|quels|quelle|quelles) (est le |sont les |)(titre|sujet|mail)s?\b',
            r'\b(donne|donner|dis|dire|balance|balancer) (moi |)(le |les |)(titre|sujet)s?\b',
            r'\b(liste|lister) (les |)(titre|sujet|mail)s?\b',
            r'\b(c\'est quoi|cest quoi|quoi comme|quest-ce que) (mes |les |)(mail|message)s?\b',
            r'\b(quels sont|lesquels|y a quoi comme) (mes |les |)mails?\b',
            r'\bmails? (non lus?|que jai pas lus?|pas encore lus?)\b',
            r'\b(les |)(mails?|messages?) (que |qu\' |)(j\'ai pas|jai pas|je n\'ai pas|pas encore) lus?\b',
            r'\b(ceux|celui) que (j\'ai pas|jai pas) lus?\b',
        ]
    },
    {
        "intent": "read",
        "patterns": [
            r'\b(lis|lire|lit|affiche|afficher|montre|montrer|voir) (mes |les |)mails?\b',
            r'\bcheck (mes |)mails?\b',
            r'\b(regarde|regarder|consulte|consulter) (mes |les |)mails?\b',
            r'\b(ouvre|ouvrir) (mes |les |)mails?\b',
            r'\b(verifie|verifier) (mes |les |)mails?\b',
        ]
    }
]