from flask import Flask, render_template, request, jsonify, redirect, url_for
import random
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Carga el archivo .env automáticamente
load_dotenv()

app = Flask(__name__)

# ==========================
#  SUPABASE CONFIG
# ==========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL o SUPABASE_KEY no están configuradas")

# TIP: SUPABASE_URL debe ser https://xxxx.supabase.co
# TIP: SUPABASE_KEY debe ser publishable/anon (NO service_role)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CHAT_ID = "Lizbeth"  # identificador del chat (puedes cambiarlo)
PAGE_SIZE = 25       # mensajes por “página” (scroll hacia arriba)

# ==========================
#  FRASES
# ==========================
EMOCIONES = {
    "ternura": [
        "Cada que veo un mensaje tuyo me acuerdo del primero que te mande, como si no te conociera y todo empezara de cero.",
        "Eres un mundo al que quiero conocer por cielo y tierra.",
        "Me gustaria saber que se siente mirarte a los ojos, no se si me ponga nervioso",
        "En cualquier momento nos podemos dejar de hablar pero yo se que te seguiras acordando de mi.",
        "Yo se que somos mundos diferentes porque sabemos que ambos somos como agua y aceite pero quiero sentir esa adrenalina contigo."
    ],
    "risa": [
        "Quieres jugar otro juego mas comprometido? se tienen que respetar las reglas",
        "Subierias una montaña conmigo?",
        "Seguro pusiste cara rara leyendo mis ocurrencias 😂",
        "Grabate todo de mi porque no soy un video para que le des retroceder",
        "No te coqueteo… solo me sale natural y si lo ves coqueteo avisame.",
        "Saldrias de noche conmigo y no regresar hasta el dia siguiente cansada pero contenta?",
    ],
    "picante": [
        "¿Qué harías si te robo un beso así de la nada? 😏",
        "¿Te dejarías que yo mande… y tú solo me sigas el juego? 🔥",
        "¿Qué harías si te beso el cuello y te jalo suave hacia mí? 😈",
        "¿Qué harías si cierro la puerta y empiezo a besarte despacio? 💘",
        "¿Qué harías si te susurro al oído y te pongo nerviosa con una sola frase? 🖤",
        "No tengo prisa contigo… pero el deseo se acumula y se nota 😌🔥",
    ],
    "sorpresa": [
        "Irias por CDMX conmigo a 10 lados diferentes yo los escojo y tu escoges el ultimo",
        "Tu y yo en la oscuridad y que solo nuestras manos sientan y vean lo que esta pasando",
        "Quiero verte en persona pero eso es algo que se dara natural y sin presiones",
        "Me dejarias entrar a tu mente?",
        "Que todo esto sea un secreto, no le dire a nadie, los tesoros se guardan bien"
    ]
}

# ==========================
#  HELPERS SUPABASE
# ==========================
def guardar_mensaje(de: str, texto: str):
    # Nunca borramos. Siempre insert.
    supabase.table("mensajes").insert({
        "chat": CHAT_ID,
        "de": de,
        "texto": texto
    }).execute()

def obtener_pagina(page: int):
    """
    Devuelve una 'página' de mensajes:
    page=0 -> los más nuevos
    page=1 -> los siguientes más viejos, etc.
    Regresa en orden viejo->nuevo para pintar fácil.
    """
    if page < 0:
        page = 0

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE - 1

    res = (
        supabase.table("mensajes")
        .select("id, de, texto, created_at")
        .eq("chat", CHAT_ID)
        .order("created_at", desc=True)   # trae más nuevos primero
        .range(start, end)
        .execute()
    )

    data = res.data if res.data else []
    data.reverse()  # ahora viejo -> nuevo
    return data

def obtener_nuevos(after_id: int):
    """
    Devuelve SOLO mensajes con id > after_id, en orden viejo->nuevo.
    Esto evita parpadeo (no se re-dibuja todo).
    """
    if after_id is None:
        after_id = 0

    res = (
        supabase.table("mensajes")
        .select("id, de, texto, created_at")
        .eq("chat", CHAT_ID)
        .gt("id", after_id)
        .order("created_at", desc=False)  # viejo -> nuevo
        .execute()
    )

    return res.data if res.data else []

# ==========================
#  ROUTES
# ==========================
@app.route("/")
def home():
    return redirect(url_for("app_view"))

@app.route("/app", methods=["GET", "POST"])
def app_view():
    frase = None

    if request.method == "POST":
        # Generar frase por emoción
        if "emocion" in request.form:
            emo = request.form["emocion"]
            if emo in EMOCIONES:
                frase = random.choice(EMOCIONES[emo])
                return redirect(url_for("app_view", f=frase))

        # Mensaje de ella
        if "pregunta" in request.form:
            texto = request.form["pregunta"].strip()
            if texto:
                guardar_mensaje("ella", texto)
            return redirect(url_for("app_view"))

    frase = request.args.get("f")
    return render_template(
        "index.html",
        frase_generada=frase,
        chat_url=url_for("estado")
    )

@app.route("/panel_miguel", methods=["GET"])
def panel():
    return render_template(
        "miguel.html",
        chat_url=url_for("estado"),
        post_url=url_for("post_miguel")
    )

@app.route("/post_miguel", methods=["POST"])
def post_miguel():
    texto = request.form.get("respuesta", "").strip()
    if texto:
        guardar_mensaje("miguel", texto)
    return redirect(url_for("panel"))

@app.route("/estado")
def estado():
    """
    Modos:
    - /estado?page=0  -> pagina (scroll viejo)
    - /estado?after_id=123 -> solo nuevos (sin parpadeo)
    """
    after_id = request.args.get("after_id")
    if after_id is not None:
        try:
            after_id = int(after_id)
        except:
            after_id = 0
        msgs = obtener_nuevos(after_id)
        return jsonify({
            "mode": "after_id",
            "after_id": after_id,
            "mensajes": msgs
        })

    # default por páginas
    page = request.args.get("page", "0")
    try:
        page = int(page)
    except:
        page = 0

    msgs = obtener_pagina(page)
    return jsonify({
        "mode": "page",
        "page": page,
        "page_size": PAGE_SIZE,
        "mensajes": msgs
    })

@app.route("/favicon.ico")
def favicon():
    return ("", 204)

if __name__ == "__main__":
    app.run(debug=True)
