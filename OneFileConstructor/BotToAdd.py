import json

import telebot
from telebot.types import *

bot = telebot.TeleBot("")
print(f"https://t.me/{bot.get_me().username}")
tokens = {

}
links = {

}


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
            bot.send_message(message.from_user.id, f'Меню для изменения бота',
                             reply_markup=InlineKeyboardMarkup()
                             .row(InlineKeyboardButton("Команды", callback_data="add_command"),
                                  InlineKeyboardButton("Текст", callback_data="add_text")))
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(message.from_user.id, "Такого бота не существует!")
    else:
        msg = bot.send_message(message.from_user.id,
                               "Нужно написать в формате \n```\ndddddddddd:ccccccccccccccccccccccccccccccccccc\n```"
                               "Где *d* это цифра, а *c* это случайный символы", parse_mode='MarkdownV2')

        bot.register_next_step_handler(msg, set_token)


def get_all_commands(user_id: int):
    with open(f"{telebot.TeleBot(tokens[user_id]).get_me().username}.json", "r", encoding="utf-8") as file:
        return [*json.load(file)["commands"]]


@bot.callback_query_handler(func=lambda call: call.data == 'add_command')
def callback(call: CallbackQuery):
    all_commands = get_all_commands(call.from_user.id)
    commands_keyboard = ReplyKeyboardMarkup()
    if len(all_commands) > 0:
        for command in all_commands:
            commands_keyboard.add(command)
    msg = bot.send_message(call.from_user.id,
                           "Вот все твои команды, выбери из списка или напиши название новой",
                           reply_markup=commands_keyboard)

    bot.register_next_step_handler(msg, set_command)


def set_command(message: Message):
    with open(f"{telebot.TeleBot(tokens[message.from_user.id]).get_me().username}.json", "r", encoding="utf-8") as file:
        commands = json.load(file)["commands"]
        print(commands)
        if message.text in commands.keys():
            print("yeeees")
        else:
            print("noooo")


bot.infinity_polling()
