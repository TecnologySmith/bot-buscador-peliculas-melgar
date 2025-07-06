from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from openpyxl import load_workbook
import os

api_id = 23820344
api_hash = 'df4339ef81253bad2463a65ae5b7b300'
bot_token = "7394299007:AAF-Fjh0xtEDDx862APrFGDz8wQI7Dizb3I"

app = Client("bot_busqueda_avanzado", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
excel_file = "canales_creados.xlsx"

user_results = {}
user_indexes = {}

@app.on_message(filters.text & (filters.private | filters.group | filters.channel))
def buscar_pelicula(client, message):
    if not message.text.lower().startswith("por favor quiero ver"):
        return

    query = message.text.lower().replace("por favor quiero ver", "").strip()
    if not query:
        message.reply("❗ Por favor escribe el nombre de la película después de 'por favor quiero ver'")
        return

    user_id = message.from_user.id if message.from_user else message.sender_chat.id

    if not os.path.exists(excel_file):
        message.reply("⚠️ No hay películas registradas.")
        return

    wb = load_workbook(excel_file)
    ws = wb.active

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        nombre, enlace, genero, imagen_url, mensaje = row[:5]
        if query in str(nombre).lower() or query in str(genero).lower() or query in str(mensaje).lower():
            results.append({
                "nombre": nombre,
                "enlace": enlace,
                "imagen_url": imagen_url
            })
        if len(results) >= 20:
            break

    if not results:
        message.reply("❌ No se encontraron resultados.")
        return

    user_results[user_id] = results
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
        except Exception as e:
            client.send_message(chat_id, f"{texto}\n⚠️.")

    user_indexes[user_id] = next_index

    if next_index < len(results):
        botones = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Ver más resultados", callback_data=f"ver_mas_{user_id}")]
        ])
        client.send_message(chat_id, "¿Quieres ver más resultados?", reply_markup=botones)
    else:
        # Último mensaje con botón al sitio web
        sitio = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Ir al sitio web", url="https://tecnologysmith.github.io/Peliculas_Melgar.html")]
        ])
        client.send_message(chat_id, "🎞️ Encuentra todas las películas en nuestra página:", reply_markup=sitio)

@app.on_callback_query(filters.regex(r"ver_mas_(\d+)"))
def ver_mas(client, callback_query: CallbackQuery):
    user_id = int(callback_query.matches[0].group(1))
    chat_id = callback_query.message.chat.id
    callback_query.answer()
    enviar_resultados(client, chat_id, user_id)

print("🎬 Bot de búsqueda de películas iniciado.")
app.run()
