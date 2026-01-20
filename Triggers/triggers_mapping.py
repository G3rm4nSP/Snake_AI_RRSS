# /Triggers/triggers_mapping.py
# Este diccionario unifica comentarios y donaciones
# Comentario exacto o cantidad mínima de donación activa el trigger
TRIGGERS = {
    1: {"gift": "guantes boxeo",  "donation": 10,     "comment": "!Mapa +"},
    2: {"gift": "perfume",        "donation": 20,     "comment": "!Mapa -"},
    3: {"gift": "lite dino",      "donation": 10,     "comment": "!Vel +"},
    4: {"gift": "big rose",       "donation": 10,     "comment": "!Vel -"},
    5: {"gift": "rose",           "donation": 1,      "comment": "!Fruta"},
    6: {"gift": "finger heart",   "donation": 5,      "comment": "!Len +"},
    7: {"gift": "flowers s",      "donation": 20,     "comment": "!Mina"},
    8: {"gift": "rosquilla",      "donation": 30,     "comment": "!Len -"},
    9: {"gift": "confeti",        "donation": 100,    "comment": "!Reset"},
    0: {"gift": "Capibara",       "donation": 30,     "comment": "!+10"},
    10: {"gift": None,            "donation": None,   "comment": "!coin"}  # solo comentario
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

def get_key_from_tiktok_donation(gift_name):
    gift_name = gift_name.lower().strip()

    for key, data in TRIGGERS.items():
        gift = data.get("gift")
        if gift and gift.lower() == gift_name:
            return key

    return None

