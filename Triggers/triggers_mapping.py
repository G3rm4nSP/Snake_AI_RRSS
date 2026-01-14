# /Triggers/triggers_mapping.py
# Este diccionario unifica comentarios y donaciones
# Comentario exacto o cantidad mínima de donación activa el trigger
TRIGGERS = {
    1: {"donation": 5, "comment": "!Mapa +"},
    2: {"donation": 10, "comment": "!Mapa -"},
    3: {"donation": 4, "comment": "!Vel +"},
    4: {"donation": 4, "comment": "!Vel -"},
    5: {"donation": 1, "comment": "!Fruta"},
    6: {"donation": 2, "comment": "!Grow"},
    7: {"donation": 6, "comment": "!Mina"},
    8: {"donation": 7, "comment": "!Shrink"},
    9: {"donation": 20, "comment": "!Reset"},
    0: {"donation": 15, "comment": "!+10"},
    10: {"donation": None, "comment": "!coin"}  # solo comentario
}

def get_key_from_comment(comment):
    comment = comment.lower().strip()
    for key, data in TRIGGERS.items():
        if data.get("comment") and data["comment"].lower() == comment:
            return key
    return None

def get_key_from_donation(amount):
    for key, data in TRIGGERS.items():
        if data.get("donation") and amount >= data["donation"]:
            return key
    return None
