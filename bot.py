from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

import unicodedata
import os
import random
import json
import requests

from flask import Flask
from threading import Thread


# ---------- CONFIG ----------
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

app = Client("bot_peliculas_lista", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

users_file = "usuarios.txt"
busquedas_file = "busquedas.json"

user_results = {}
user_pages = {}

# GOOGLE SHEETS JSON
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_cQK1aAJh7LWCubb_9IUnBQvieHUA-0k/gviz/tq?tqx=out:json"


# ---------- SERVIDOR WEB (Render) ----------
web = Flask('')

@web.route('/')
def home():
    return "Bot Peliculas Melgar activo"

def run_web():
    web.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()


# ---------- CONTADOR USUARIOS ----------
def guardar_usuario(user_id):

    if not os.path.exists(users_file):
        with open(users_file, "w") as f:
            f.write(str(user_id) + "\n")
        return

    with open(users_file, "r") as f:
        usuarios = f.read().splitlines()

    if str(user_id) not in usuarios:
        with open(users_file, "a") as f:
            f.write(str(user_id) + "\n")


def contar_usuarios():

    if not os.path.exists(users_file):
        return 0

    with open(users_file, "r") as f:
        return len(f.read().splitlines())


# ---------- NORMALIZAR ----------
def normalizar(texto):

    texto = str(texto).lower()
    texto = unicodedata.normalize('NFD', texto)

    return ''.join(
        c for c in texto if unicodedata.category(c) != 'Mn'
    )


# ---------- CARGAR PELICULAS DESDE GOOGLE SHEETS ----------
def cargar_peliculas():

    try:

        r = requests.get(SHEET_URL)

        data = r.text

        json_data = json.loads(data[47:-2])

        rows = json_data["table"]["rows"]

        peliculas = []

        for row in rows:

            nombre = row["c"][0]["v"] if row["c"][0] else ""
            genero = row["c"][2]["v"] if row["c"][2] else ""
            imagen = row["c"][3]["v"] if row["c"][3] else ""
            enlace = row["c"][6]["v"] if row["c"][6] else ""

            if nombre and enlace:

                peliculas.append({
                    "nombre": nombre,
                    "genero": genero,
                    "imagen": imagen,
                    "enlace": enlace
                })

        return peliculas

    except Exception as e:

        print("Error cargando peliculas:", e)

        return []


# ---------- GUARDAR BUSQUEDAS ----------
def registrar_busqueda(nombre):

    data = {}

    if os.path.exists(busquedas_file):

        with open(busquedas_file) as f:
            data = json.load(f)

    data[nombre] = data.get(nombre, 0) + 1

    with open(busquedas_file, "w") as f:
        json.dump(data, f)


# ---------- TOP BUSCADAS ----------
def top_buscadas():

    if not os.path.exists(busquedas_file):
        return []

    with open(busquedas_file) as f:
        data = json.load(f)

    ordenadas = sorted(data.items(), key=lambda x: x[1], reverse=True)

    peliculas = cargar_peliculas()

    top = []

    for nombre, _ in ordenadas[:10]:

        for peli in peliculas:

            if peli["nombre"] == nombre:
                top.append(peli)

    return top


# ---------- BOTONES PROMO ----------
def botones_promocion():

    botones = [

        [InlineKeyboardButton("🎬 Página Películas Melgar",
        url="https://tecnologysmith.github.io/Peliculas_Melgar.html")],

        [InlineKeyboardButton("🚀 TecnologySmith",
        url="https://tecnologysmith.godaddysites.com/")],

    ]

    return botones


# ---------- MENU ----------
def menu_principal():

    botones = [

        [InlineKeyboardButton("🎲 Película Aleatoria", callback_data="aleatoria")],

        [InlineKeyboardButton("🔥 Más buscadas", callback_data="top")],

        [InlineKeyboardButton("🆕 Recién agregadas", callback_data="recientes")]

    ]

    return InlineKeyboardMarkup(botones)


# ---------- START ----------
@app.on_message(filters.command("start"))
def start(client, message):

    if message.from_user:
        guardar_usuario(message.from_user.id)

    total = contar_usuarios()

    message.reply(
        f"🍿 Bienvenido al buscador de películas\n\n"
        f"👥 Usuarios usando el bot: {total}\n\n"
        f"🔎 Escribe el nombre de una película o género",
        reply_markup=menu_principal()
    )


# ---------- BUSCADOR ----------
@app.on_message(filters.text & (filters.private | filters.group))
def buscador(client, message):

    if message.from_user:
        guardar_usuario(message.from_user.id)

    texto = normalizar(message.text)

    if len(texto) < 3:
        return

    peliculas = cargar_peliculas()

    palabras = texto.split()

    resultados = []

    for peli in peliculas:

        contenido = normalizar(
            f"{peli['nombre']} {peli['genero']}"
        )

        if all(p in contenido for p in palabras):

            resultados.append(peli)

            registrar_busqueda(peli["nombre"])

    user_id = message.from_user.id if message.from_user else message.chat.id

    if not resultados:

        client.send_message(
            message.chat.id,
            "❌ No encontramos esa película"
        )

        return

    random.shuffle(resultados)

    user_results[user_id] = resultados
    user_pages[user_id] = 0

    mostrar_lista(client, message.chat.id, user_id)


# ---------- MOSTRAR LISTA ----------
def mostrar_lista(client, chat_id, user_id):

    resultados = user_results.get(user_id, [])

    pagina = user_pages.get(user_id, 0)

    por_pagina = 10

    inicio = pagina * por_pagina
    fin = inicio + por_pagina

    lote = resultados[inicio:fin]

    texto = "🎬 Películas encontradas\n\n"

    for i, peli in enumerate(lote, start=inicio + 1):

        texto += f'{i}. <a href="{peli["enlace"]}">{peli["nombre"]}</a>\n'

    botones = []

    if fin < len(resultados):
        botones.append([InlineKeyboardButton("➡ Siguiente", callback_data="siguiente")])

    botones.append([InlineKeyboardButton("🎲 Aleatoria", callback_data="aleatoria")])

    teclado = botones + botones_promocion()

    client.send_message(
        chat_id,
        texto,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(teclado)
    )


# ---------- SIGUIENTE ----------
@app.on_callback_query(filters.regex("^siguiente$"))
def siguiente(client, callback_query):

    user_id = callback_query.from_user.id

    user_pages[user_id] += 1

    mostrar_lista(client, callback_query.message.chat.id, user_id)

    callback_query.answer()


# ---------- ALEATORIA ----------
@app.on_callback_query(filters.regex("^aleatoria$"))
def aleatoria(client, callback_query):

    peliculas = cargar_peliculas()

    peli = random.choice(peliculas)

    texto = f'🎬 <a href="{peli["enlace"]}">{peli["nombre"]}</a>'

    client.send_message(
        callback_query.message.chat.id,
        texto,
        parse_mode=ParseMode.HTML
    )

    callback_query.answer()


# ---------- TOP BUSCADAS ----------
@app.on_callback_query(filters.regex("^top$"))
def top(client, callback_query):

    top = top_buscadas()

    texto = "🔥 Películas más buscadas\n\n"

    for i, peli in enumerate(top, start=1):

        texto += f'{i}. <a href="{peli["enlace"]}">{peli["nombre"]}</a>\n'

    client.send_message(
        callback_query.message.chat.id,
        texto,
        parse_mode=ParseMode.HTML
    )

    callback_query.answer()


# ---------- RECIENTES ----------
@app.on_callback_query(filters.regex("^recientes$"))
def recientes(client, callback_query):

    peliculas = cargar_peliculas()

    recientes = peliculas[-10:]

    texto = "🆕 Películas recién agregadas\n\n"

    for i, peli in enumerate(recientes, start=1):

        texto += f'{i}. <a href="{peli["enlace"]}">{peli["nombre"]}</a>\n'

    client.send_message(
        callback_query.message.chat.id,
        texto,
        parse_mode=ParseMode.HTML
    )

    callback_query.answer()


print("🎬 Bot de películas iniciado correctamente")

keep_alive()

app.run()
