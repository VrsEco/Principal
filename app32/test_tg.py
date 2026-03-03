import telebot
import os

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Substitua pelo seu Chat ID se quiser testar, ou apenas ver se conecta
try:
    me = bot.get_me()
    print(f"Bot info: {me.username}")
except Exception as e:
    print(f"Error connecting: {e}")
