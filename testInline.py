import telebot
from telebot.callback_data import CallbackData
from telebot.storage import StateMemoryStorage
from telebot.types import *

bot = telebot.TeleBot("",
                      state_storage=StateMemoryStorage())

test_callback = CallbackData("type", "content", prefix="test")


@bot.message_handler(commands=['start'])
def start(message: Message):
    bot.send_message(message.from_user.id, "КНОПКИ!", reply_markup=InlineKeyboardMarkup().
                     row(InlineKeyboardButton(text="test",
                                              callback_data=test_callback.new(type="kgerge", content=23))))


@bot.callback_query_handler(func=lambda call: True)
def callback(call: CallbackQuery):
    print(type(call.data.split(":")))


bot.infinity_polling()
