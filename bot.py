import sys
import os
import warnings
import discord
from discord.ext import commands
import yt_dlp
import syncedlyrics
import asyncio
import time
import re
from dotenv import load_dotenv

# Ignorar advertencias de deprecación internas en la consola
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Forzar codificación UTF-8 en la consola de
# Windows para evitar errores con emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de Intents y Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Estructura global para manejar la cola de canciones por servidor
song_queues = {}

# Configuración de yt-dlp y FFmpeg
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'js_runtimes': {'node': {}},
    'extractor_args': {'youtube': ['player_client=android']}
}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

FFMPEG_OPTIONS = {
    'before_options': (
        '-reconnect 1 -reconnect_streamed 1 '
        '-reconnect_delay_max 5'
    ),
    'options': '-vn'
}


# Función para procesar el archivo .lrc
def parse_lrc(lrc_text):
    """Convierte el texto LRC en una lista de
    tuplas: (segundos, linea_de_texto)"""
    lyrics_data = []
    # Busca el patrón [minutos:segundos.milisegundos]
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')

    for line in lrc_text.split('\n'):
        match = pattern.match(line)
        if match:
            minutos, segundos, texto = match.groups()
            tiempo_total = int(minutos) * 60 + float(segundos)
            # Ignoramos líneas vacías o instrumentales largos sin texto
            if texto.strip():
                lyrics_data.append((tiempo_total, texto.strip()))

    return lyrics_data


# Tarea asíncrona para actualizar la letra (El Karaoke)
async def actualizar_letra(mensaje, letras, tiempo_inicio, titulo):
    indice_actual = -1

    while True:
        vc = mensaje.guild.voice_client
        if not vc or not vc.is_playing():
            break

        tiempo_transcurrido = time.time() - tiempo_inicio
        nuevo_indice = -1

        for i, (tiempo_linea, _) in enumerate(letras):
            if tiempo_transcurrido >= tiempo_linea:
                nuevo_indice = i
            else:
                break

        if nuevo_indice != indice_actual and nuevo_indice != -1:
            indice_actual = nuevo_indice

            linea_ant = (
                letras[indice_actual - 1][1]
                if indice_actual > 0
                else ""
            )
            linea_act = f"**🟢 {letras[indice_actual][1]}**"
            linea_sig = (
                letras[indice_actual + 1][1]
                if indice_actual < len(letras) - 1
                else ""
            )

            descripcion = f"*{linea_ant}*\n\n{linea_act}\n\n*{linea_sig}*"
            embed = discord.Embed(
                title=f"🎤 Karaoke: {titulo}",
                description=descripcion,
                color=discord.Color.purple(),
            )

            try:
                await mensaje.edit(embed=embed)
            except discord.HTTPException:
                pass

        await asyncio.sleep(0.5)

    try:
        embed_fin = discord.Embed(
            title=f"🎤 Karaoke: {titulo}",
            description="¡Canción terminada!",
            color=discord.Color.dark_gray(),
        )
        await mensaje.edit(embed=embed_fin)
    except discord.HTTPException:
        pass


# Reproductor de colas de canciones
async def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id in song_queues and len(song_queues[guild_id]) > 0:
        cancion = song_queues[guild_id].pop(0)
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return

        executable = (
            "ffmpeg.exe" if os.path.exists("ffmpeg.exe") else "ffmpeg"
        )
        audio_source = discord.FFmpegPCMAudio(
            cancion['url_audio'],
            executable=executable,
            **FFMPEG_OPTIONS
        )

        def after_playing(error):
            if error:
                print(f"Error en reproducción: {error}")
            asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop
            )

        vc.play(audio_source, after=after_playing)
        tiempo_inicio = time.time()

        if cancion['letras']:
            embed = discord.Embed(
                title=f"🎤 Karaoke: {cancion['titulo']}",
                description="Preparando micrófono...",
                color=discord.Color.purple()
            )
            mensaje_letra = await ctx.send(embed=embed)
            asyncio.create_task(
                actualizar_letra(
                    mensaje_letra,
                    cancion['letras'],
                    tiempo_inicio,
                    cancion['titulo']
                )
            )
        else:
            msg = (
                f"🎵 Reproduciendo: **{cancion['titulo']}**\n"
                "*(No encontré letra sincronizada para esta canción)*"
            )
            await ctx.send(msg)


# Comandos del bot
@bot.command()
async def play(ctx, *, busqueda):
    if not ctx.author.voice:
        return await ctx.send("❌ ¡Debes estar en un canal de voz primero!")

    canal_voz = ctx.author.voice.channel
    vc = ctx.voice_client

    if not vc:
        vc = await canal_voz.connect()
    elif vc.channel != canal_voz:
        await vc.move_to(canal_voz)

    mensaje_estado = await ctx.send(
        f"🔎 Buscando `{busqueda}` y descargando letras..."
    )

    try:
        loop = asyncio.get_running_loop()
        datos = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(
                f"ytsearch:{busqueda}", download=False
            )
        )

        if 'entries' in datos and len(datos['entries']) > 0:
            info = datos['entries'][0]
        else:
            info = datos

        url_audio = info['url']
        titulo = info['title']
    except Exception as e:
        await mensaje_estado.edit(content=f"❌ Error al buscar la canción: {e}")
        return

    letra_cruda = None
    try:
        letra_cruda = await loop.run_in_executor(
            None, lambda: syncedlyrics.search(titulo)
        )
    except Exception as e:
        print(f"Error buscando letras: {e}")

    letras_procesadas = parse_lrc(letra_cruda) if letra_cruda else None

    cancion = {
        'titulo': titulo,
        'url_audio': url_audio,
        'letras': letras_procesadas
    }

    guild_id = ctx.guild.id
    if guild_id not in song_queues:
        song_queues[guild_id] = []

    if vc.is_playing() or vc.is_paused():
        song_queues[guild_id].append(cancion)
        posicion = len(song_queues[guild_id])
        await mensaje_estado.edit(
            content=(
                f"➕ Añadido a la cola (Posición #{posicion}): "
                f"**{titulo}**"
            )
        )
    else:
        await mensaje_estado.delete()
        song_queues[guild_id].append(cancion)
        await play_next(ctx)


@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await ctx.send("⏭️ Canción omitida.")
    else:
        await ctx.send("❌ No hay ninguna canción reproduciéndose.")


@bot.command(aliases=['cola'])
async def queue(ctx):
    guild_id = ctx.guild.id
    cola = song_queues.get(guild_id, [])

    if not cola:
        return await ctx.send("📜 La cola de canciones está vacía.")

    lineas = []
    for i, cancion in enumerate(cola, start=1):
        lineas.append(f"**{i}.** {cancion['titulo']}")

    descripcion = "\n".join(lineas[:10])
    if len(cola) > 10:
        descripcion += f"\n\n*...y {len(cola) - 10} canciones más.*"

    embed = discord.Embed(
        title="📜 Cola de Reproducción",
        description=descripcion,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")


@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música reanudada.")


@bot.command()
async def stop(ctx):
    guild_id = ctx.guild.id
    if guild_id in song_queues:
        song_queues[guild_id].clear()

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Me desconecté y limpié la cola de canciones.")
    else:
        await ctx.send("❌ No estoy conectado a ningún canal de voz.")


# Evento de inicio
@bot.event
async def on_ready():
    print(f'Bot conectado exitosamente como {bot.user}')

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: No se encontró la variable DISCORD_TOKEN en el archivo .env")
