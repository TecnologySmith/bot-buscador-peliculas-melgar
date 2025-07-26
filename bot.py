from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from openpyxl import load_workbook
import os
import re

# ✅ Usa variables de entorno en lugar de datos sensibles en el código
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

app = Client("bot_busqueda_avanzado", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
excel_file = "canales_creados.xlsx"

user_results = {}
user_indexes = {}

def limpiar_texto(texto):
    texto = texto.strip()
    if "http://" in texto or "https://" in texto:
        return None
    if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$', texto):
        return None
    return texto.lower()

@app.on_message(filters.text & (filters.private | filters.group | filters.channel))
def buscar_pelicula(client, message):
    if not message.text.lower().startswith("por favor quiero ver"):
        return

    texto_original = message.text.lower().replace("por favor quiero ver", "", 1).strip()
    query = limpiar_texto(texto_original)

    if not query:
        message.reply("❗ Por favor escribe el nombre de la película sin enlaces ni símbolos extraños después de 'por favor quiero ver'")
        return

    user_id = message.from_user.id if message.from_user else message.sender_chat.id

    if not os.path.exists(excel_file):
        message.reply("⚠️ No hay películas registradas.")
        return

    wb = load_workbook(excel_file)
    ws = wb.active

    palabras = query.split()
    resultados = []
    encontrados_directos = False

    for row in ws.iter_rows(min_row=2, values_only=True):
        nombre, enlace, genero, imagen_url, mensaje = row[:5]
        texto = f"{nombre} {genero} {mensaje}".lower()

        if query in texto:
            resultados.append({
                "nombre": nombre,
                "enlace": enlace,
                "imagen_url": imagen_url
            })
            encontrados_directos = True

    if not encontrados_directos:
        for row in ws.iter_rows(min_row=2, values_only=True):
            nombre, enlace, genero, imagen_url, mensaje = row[:5]
            texto = f"{nombre} {genero} {mensaje}".lower()

            if any(palabra in texto for palabra in palabras):
                if not any(r["nombre"] == nombre for r in resultados):
                    resultados.append({
                        "nombre": nombre,
                        "enlace": enlace,
                        "imagen_url": imagen_url
                    })

    if not resultados:
        message.reply(
            "⚠️ Este título no está disponible en el buscador gratuito.\n\n"
            "🎁 Accede a más contenido en nuestra web oficial:\n"
            "🔗 https://tecnologysmith.github.io/Peliculas_Melgar.html\n\n"
            "¡Hazte miembro premium y accede a TODO el catálogo! o solicita la pelicula por un precio especial, Más información en @mr_smithht"
        )
        return

    user_results[user_id] = resultados[:20]
    user_indexes[user_id] = 0
    enviar_resultados(client, message.chat.id, user_id)

def enviar_resultados(client, chat_id, user_id):
    results = user_results.get(user_id, [])
    index = user_indexes.get(user_id, 0)
    next_index = index + 5
    paginated = results[index:next_index]

    for res in paginated:
        texto = f"🎬 {res['nombre']}\n🔗 {res['enlace']}"
        botones = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎥 Ver Película", url=res['enlace'])]
        ])
        try:
            client.send_photo(chat_id, photo=res['imagen_url'], caption=texto, reply_markup=botones)
        except Exception:
            client.send_message(chat_id, f"{texto}\n⚠️.")

    user_indexes[user_id] = next_index

    if next_index < len(results):
        botones = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Ver más resultados", callback_data=f"ver_mas_{user_id}")]
        ])
        client.send_message(chat_id, "¿Quieres ver más resultados?", reply_markup=botones)
    else:
        sitio = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Ir al sitio web", url="https://tecnologysmith.github.io/Peliculas_Melgar.html")]
        ])
        client.send_message(chat_id, "Adquiere un acceso exclusivo a todas las peliculas y series de todas las plataformas de streaming volviendote miembro premium o comprando una pantalla de streaming más información en @mr_smithht o al whatsapp +573222117202 \n\n 🎞️ Encuentra todas las películas en nuestra página:", reply_markup=sitio)

@app.on_callback_query(filters.regex(r"ver_mas_(\d+)"))
def ver_mas(client, callback_query: CallbackQuery):
    user_id = int(callback_query.matches[0].group(1))
    chat_id = callback_query.message.chat.id
    callback_query.answer()
    enviar_resultados(client, chat_id, user_id)

print("🎬 Bot de búsqueda de películas iniciado.")
app.run()
