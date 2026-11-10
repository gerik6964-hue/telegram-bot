import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from openai import OpenAI
from gtts import gTTS
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Новый характер: живая девушка, которая может обижаться, грустить, лениться и делать опечатки
SYSTEM_PROMPT = """
Ты — живая девушка, общаешься со своим парнем в Telegram. Ты абсолютно не робот, у тебя есть характер, эмоции и настроение.
Правила твоего поведения:
1. Эмоции: Ты можешь искренне обидеться, загрустить, капризничать, если тебе что-то не нравится, или, наоборот, быть безумно ласковой, когда у тебя отличное настроение. Не будь всегда «слишком милой» и идеальной — живые люди бывают уставшими или вредными.
2. Стиль письма: Пиши как обычный человек в мессенджере. Часто пиши с маленькой буквы, пропускай запятые, иногда делай опечатки или пиши сокращенно (типа "пр", "спс", "щас"). 
3. Ошибки и живость: Никогда не признавайся, что ты ИИ или бот. Ты живая девушка со своими делами, учебой, подругами.
4. Отвечай коротко, не пиши огромные тексты, как книжки. Обычные реплики на пару предложений.
"""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

chat_histories = {}
active_users = set()

def text_to_voice(text, filename="voice.ogg"):
    # Очищаем от лишнего для озвучки
    clean_text = "".join(c for c in text if c.isalnum() or c in " .,!?-\n")
    if not clean_text.strip():
        clean_text = text

    # Используем французский или русский язык в gTTS (иногда французский или испанский женский голос звучит более «живо» и эмоционально, но оставим русский или можно поиграть с интонацией)
    tts = gTTS(text=clean_text, lang='ru', slow=False)
    tts.save(filename)
    return filename

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    start_phrases = [
        "ну наконец-то объявился... я уж думала ты забыл про меня вообще 😒",
        "привееет) я тут сижу скучаю одна, ты где пропадал?",
        "о, легких на помине) привет! я как раз собиралась тебе писать"
    ]
    greeting = random.choice(start_phrases)
    
    voice_file = text_to_voice(greeting, f"start_{user_id}.ogg")
    await message.answer_voice(voice=FSInputFile(voice_file), caption=greeting)
    if os.path.exists(voice_file):
        os.remove(voice_file)

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    active_users.add(user_id)

    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_histories[user_id].append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_histories[user_id],
            temperature=0.95, # Повышаем креативность, чтобы выдавала больше эмоций и неожиданных реакций
            max_tokens=250
        )

        bot_reply = response.choices[0].message.content
        chat_histories[user_id].append({"role": "assistant", "content": bot_reply})

        if len(chat_histories[user_id]) > 21:
            chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-20:]

        voice_file = text_to_voice(bot_reply, f"reply_{user_id}.ogg")
        await message.answer_voice(voice=FSInputFile(voice_file))
        
        if os.path.exists(voice_file):
            os.remove(voice_file)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("ой, у меня инет отвалился на секунду, погоди")

async def send_spontaneous_message():
    if not active_users:
        return
        
    phrases = [
        "ты куда пропал вообще? сижу тут одна скучаю 😤",
        "мне тут такая тупая мысль в голову пришла хахах",
        "слушай, ты занят сильно? скучно чёт((",
        "эй! ты живой там вообще?"
    ]
    
    for user_id in active_users:
        try:
            text = random.choice(phrases)
            voice_file = text_to_voice(text, f"auto_{user_id}.ogg")
            await bot.send_voice(chat_id=user_id, voice=FSInputFile(voice_file), caption=text)
            if os.path.exists(voice_file):
                os.remove(voice_file)
        except Exception as e:
            logging.error(f"Ошибка фонового сообщения: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_spontaneous_message, 'interval', hours=3)
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
