import json

import telebot
from telebot.types import *

bot = telebot.TeleBot("5870811802:AAE4EclZ9h_G1JvZQTmSQxe9xRajtK1LRNw")
print(f"https://t.me/{bot.get_me().username}")
tokens = {

}
print(len("5870811802:AAE4EclZ9h_G1JvZQTmSQxe9xRajtK1LRNw"))


@bot.message_handler(commands=['start'])
def start(message: Message):
    bot.send_message(message.chat.id, "Это пробный генератор ботов, нажмите на кнопку, чтобы попасть на генератор",
                     reply_markup=InlineKeyboardMarkup().add(
                         InlineKeyboardButton("Создать бота", callback_data="start")))


@bot.callback_query_handler(func=lambda call: call.data == 'start')
def callback(call: CallbackQuery):
    msg = bot.edit_message_text("Создай бота в @BotFather и отправь мне токен бота", call.from_user.id, call.message.id)

    bot.register_next_step_handler(msg, set_token)


def set_token(message: Message):
    if len(message.text) == 46 and message.text.split(":")[0].isdigit():
        try:
            to_add = telebot.TeleBot(message.text)
            with open(f"{to_add.get_me().username}.json", "w", encoding="utf-8") as file:
                json.dump({
                    "token": message.text,
                    "start": None,
                    "help": None,
                    "chatgpt": False,
                    "docs": False,
                    "commands": {},
                    "text": {}
                }, file, ensure_ascii=False)
            tokens[message.from_user.id] = message.text
            bot.send_message(message.from_user.id, "Бот добавлен!")
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(message.from_user.id, "Такого бота не существует!")
    else:
        msg = bot.send_message(message.from_user.id,
                               "Нужно написать в формате \n```\ndddddddddd:ccccccccccccccccccccccccccccccccccc\n```"
                               "Где *d* это цифра, а *c* это случайный символы", parse_mode='MarkdownV2')

        bot.register_next_step_handler(msg, set_token)


bot.infinity_polling()
