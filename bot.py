import os
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración del bot de Telegram
api_id = int(os.environ["API_ID"])  # ejemplo: 12345678
api_hash = os.environ["API_HASH"]   # ejemplo: 'abcd1234...'
bot_token = os.environ["BOT_TOKEN"] # ejemplo: '123:ABC...'

app = Client("bot_busqueda_avanzado", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Conexión con Google Sheets usando variable de entorno
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
cred_json = os.environ["GOOGLE_CREDENTIALS_JSON"]
cred_dict = json.loads(cred_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client_gs = gspread.authorize(creds)

# ID de la hoja de cálculo
SPREADSHEET_ID = "1_cQK1aAJh7LWCubb_9IUnBQvieHUA-0k"
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1

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
    palabras = query.split()
    resultados = []
    encontrados_directos = False

    try:
        rows = sheet.get_all_values()[1:]  # Omitir encabezado
    except Exception as e:
        message.reply("⚠️ No se pudo acceder a la hoja de cálculo.")
        return

    for row in rows:
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
        for row in rows:
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
        message.reply("❌ No se encontraron resultados.")
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
        except Exception as e:
            client.send_message(chat_id, f"{texto}\n⚠️ Imagen no disponible.")

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
        client.send_message(chat_id, "🎞️ Encuentra todas las películas en nuestra página:", reply_markup=sitio)

@app.on_callback_query(filters.regex(r"ver_mas_(\d+)"))
def ver_mas(client, callback_query: CallbackQuery):
    user_id = int(callback_query.matches[0].group(1))
    chat_id = callback_query.message.chat.id
    callback_query.answer()
    enviar_resultados(client, chat_id, user_id)

print("🎬 Bot de búsqueda conectado a Google Sheets y listo.")
app.run()
