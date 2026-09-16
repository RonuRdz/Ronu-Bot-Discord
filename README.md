# 🎵 Bot de Música para Discord con Modo Karaoke

Un bot de Discord desarrollado en Python que no solo reproduce música de alta calidad desde YouTube, sino que incluye un innovador **Modo Karaoke**, mostrando letras sincronizadas en tiempo real directamente en el chat mediante *embeds* dinámicos.

## ✨ Características Principales

*   **Reproducción de Audio:** Integración con `yt-dlp` y `FFmpeg` para extraer y reproducir el mejor audio disponible.
*   **Modo Karaoke (Letras Sincronizadas):** Utiliza `syncedlyrics` para buscar letras en formato LRC. El bot actualiza un mensaje incrustado (Embed) en tiempo real, resaltando la línea actual de la canción mientras se reproduce.
*   **Sistema de Colas por Servidor:** Manejo independiente de listas de reproducción para múltiples servidores de forma simultánea.
*   **Diseño Asíncrono:** Uso eficiente de `asyncio` y `loop.run_in_executor` para evitar bloqueos en el hilo principal durante la descarga de datos.

## 🛠️ Tecnologías y Librerías

*   **Lenguaje:** Python 3.8+
*   **Librería Principal:** `discord.py`
*   **Procesamiento de Audio:** `yt-dlp`, `FFmpeg`
*   **Letras:** `syncedlyrics`
*   **Variables de Entorno:** `python-dotenv`

## 📜 Comandos Disponibles

El prefijo por defecto del bot es `!`.

| Comando | Alias | Descripción |
| :--- | :--- | :--- |
| `!play <búsqueda>` | | Busca la canción, descarga las letras y la reproduce (o la añade a la cola). |
| `!skip` | | Salta la canción que se está reproduciendo actualmente. |
| `!queue` | `!cola` | Muestra hasta las próximas 10 canciones en la lista de reproducción. |
| `!pause` | | Pausa la reproducción actual. |
| `!resume` | | Reanuda una canción pausada. |
| `!stop` | | Detiene la música, limpia la cola y desconecta al bot del canal de voz. |

## 🚀 Instalación y Uso local

Si deseas clonar y probar este bot en tu propia máquina, sigue estos pasos:

### 1. Requisitos Previos
*   Tener **Python** instalado.
*   Tener **FFmpeg** instalado y agregado al PATH del sistema (o colocar el ejecutable `ffmpeg.exe` en la raíz del proyecto).

### 2. Clonar el repositorio
```bash
git clone git@github.com:RonuRdz/Ronu-Bot-Discord.git
cd Ronu-Bot-Discord
```

### 3. Instalar las dependencias
Es recomendable usar un entorno virtual. Instala los paquetes necesarios:
```bash
pip install discord.py yt-dlp syncedlyrics python-dotenv PyNaCl
```
(Nota: PyNaCl es requerido por discord.py para el soporte de voz).

### 4. Configurar las variables de entorno
Crea un archivo llamado .env en la raíz del proyecto y añade tu token de Discord:
```bash
DISCORD_TOKEN=tu_token_secreto_aqui
```

### 5. Iniciar el bot
```bash
python bot.py
```

**Si el bot no se conecta:** Verifica que el token sea correcto y que el archivo .env esté en la misma carpeta que bot.py. Para el soporte de voz, asegúrate de tener permisos adecuados en Discord y de que FFmpeg esté instalado correctamente.
