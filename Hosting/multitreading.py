import asyncio
import time
from threading import *

import openai
import requests
import speech_recognition as sr
import telebot
from html2image import Html2Image
from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from telebot.types import *
from config import *

hti = Html2Image()

openai.api_key = open_ai_key

last_message = {}
bots = []
r = sr.Recognizer()


def check_bots():
    global last_message

    while True:
        data = requests.get("http://localhost:8080/bot/updates").json()

        if data != last_message:
            last_message = data

            for i in data:
                if i not in bots:
                    print(f">> NEW BOT {i}")
                    bots.append(i)
                    info = requests.get(f"http://localhost:8080/bot?botUsername={i}").json()
                    print(info)
                    return info["idUsername"], Thread(target=Bot, args=(info['token'], info,))

        time.sleep(600)


# def set_list(name: str):
#     result = [["Команды / текст", "Значения"]]
#
#     with open(f"{name}.json") as f:
#         json_file = json.load(f)
#
#         result.append(["/start", json_file["start"]])
#         result.append(["/help", json_file["help"]])
#         for i, v in json_file["commands"].items():
#             if v["type"] == "message":
#                 result.append([f"/{i}", v["text"][:25]])
#             elif v["type"] == "photo":
#                 result.append([f"/{i}", f'<a href="{v["img"]}">photo</a><br />', v["caption"][:25]])
#
#         for i, v in json_file["text"].items():
#             result.append([i, v[:25]])
#
#         result.append(["chatgpt", json_file["chatgpt"]])
#
#     return result, name
#
#
# def get_web(tpl: tuple) -> TextIO:
#     env = Environment(loader=FileSystemLoader('templates'))
#
#     template = env.get_template('test.html')
#
#     rendered_template = template.render(nested_list=tpl[0])
#
#     with open(f'{tpl[1]}.html', 'w') as f:
#         f.write(rendered_template)
#
#         return f
#
#
# get_web(set_list('paradickmabot'))
# get_web(set_list('SoundHuntersBot'))


class Bot:

    def __init__(self, token, data):
        self.bot = telebot.TeleBot(token, state_storage=StateMemoryStorage())
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))
        self.bot.add_custom_filter(custom_filters.TextMatchFilter())

        self._username = self.bot.get_me().username

        self.handler = logging.FileHandler(f"{self._username}.log")
        self.handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))

        self.logger = logging.getLogger(self._username)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

        self.add_status_command = {}
        self.add_status_text = {}

        self.data = data

        def generate_main_keyboard(message: Message):
            keyboard = ReplyKeyboardMarkup()

            keyboard_info = requests.get(f"http://localhost:8080/bot/main/{self._username}")

            if keyboard_info != "":
                for i in keyboard_info.json():
                    row_buttons = []
                    for j in i:
                        row_buttons.append(KeyboardButton(j))
                    keyboard.row(*row_buttons)

            if requests.get(f"http://localhost:8080/user/admin/{self._username}?UserId={message.from_user.id}").json():
                keyboard.row("Редактор")

            return keyboard

        @self.bot.message_handler(commands=['start'])
        def start(message: Message):
            self.logger.info(f'{message.from_user.id} - {message.text}')
            requests.post(f"http://localhost:8080/user?BotUsername={self._username}", json={
                "fromUserId": message.from_user.id,
                "admin": False
            })

            self.bot.send_message(message.from_user.id, "Привет!",
                                  reply_markup=generate_main_keyboard(message))

        class EditorState(StatesGroup):
            editor = State()
            commands = State()
            text = State()
            wait = State()

        class CommandAddState(StatesGroup):
            CommandTitle = State()
            CommandContent = State()

        class TextAddState(StatesGroup):
            TextTitle = State()
            TextContent = State()

        class TextEditState(StatesGroup):
            findText = State()
            chooseText = State()
            editText = State()
            editTitle = State()
            editContent = State()

        class CommandEditState(StatesGroup):
            findCommand = State()
            chooseCommand = State()
            editCommand = State()
            editTitle = State()
            editContent = State()

        # ---------------------------------
        # Завершение действий
        # ---------------------------------

        @self.bot.message_handler(state="*", text="Завершить")
        def cancel_state(message: Message):
            print("cancel_state")
            # try:
            #     with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
            #         self.bot.delete_message(chat_id=message.from_user.id, message_id=fsmData['last_message'])
            # except KeyError:
            #     pass

            self.bot.send_message(message.from_user.id, "Действие отменено!", reply_markup=ReplyKeyboardMarkup().
                                  row("Команды", "Текст").row("Выйти"))

            self.bot.set_state(message.from_user.id, EditorState.editor)

        @self.bot.message_handler(state="*", text="Выйти")
        def exit_state(message: Message):
            print("exit_state")
            # try:
            #     with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
            #         self.bot.delete_message(chat_id=message.from_user.id, message_id=fsmData['last_message'])
            # except KeyError:
            #     pass

            self.bot.send_message(message.from_user.id, "Вышел!",
                                  reply_markup=generate_main_keyboard(message))

            self.bot.delete_state(message.from_user.id, message.chat.id)

        # ---------------------------------
        # Редактор панель
        # ---------------------------------

        @self.bot.message_handler(state=EditorState.editor)
        def editor(message: Message):
            if message.text == "Команды":
                self.bot.send_message(message.from_user.id,
                                      "Редактирование команд",
                                      reply_markup=ReplyKeyboardMarkup().
                                      row("Добавить команду").row("Редактировать команды").row("Завершить"))

            elif message.text == "Текст":
                self.bot.send_message(message.from_user.id, "Редактирование текста",
                                      reply_markup=ReplyKeyboardMarkup().
                                      row("Добавить текст").row("Редактировать текст").row("Завершить"))

            self.bot.set_state(message.from_user.id, EditorState.wait)

        # ---------------------------------
        # Добавление команд
        # ---------------------------------

        @self.bot.message_handler(state=EditorState.wait, text="Добавить команду")
        def add_command_start(message: Message):
            self.bot.send_message(message.from_user.id,
                                  "Пришлите команду в формате -> <command>\n\nБЕЗ /",
                                  reply_markup=ReplyKeyboardRemove())

            self.bot.set_state(message.from_user.id, CommandAddState.CommandTitle, message.chat.id)

        @self.bot.message_handler(state=CommandAddState.CommandTitle)
        def add_command_title(message: Message):
            if message.text.startswith("/"):
                self.bot.send_message(message.from_user.id, "Нужно написать просто слово без /!")
                return

            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                fsmData['commandTitle'] = message.text

            self.bot.send_message(message.from_user.id,
                                  "Пришлите что хотите получать при написании этой команды!")

            self.bot.set_state(message.from_user.id, CommandAddState.CommandContent, message.chat.id)

        @self.bot.message_handler(state=CommandAddState.CommandContent, content_types=['photo', 'text'])
        def add_command_content(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                requests.post(url=f"http://localhost:8080/command?botUsername={self._username}", json={
                    "name": fsmData['commandTitle'],
                    "type": message.content_type,
                    "text": message.text,
                    "image": message.photo[-1].file_id if message.photo is not None else None,
                    "caption": message.caption,
                })

            self.bot.send_message(message.from_user.id, "Команда успешно добавлена!",
                                  reply_markup=ReplyKeyboardMarkup().row("Команды", "Текст").row("Выйти"))

            self.bot.set_state(message.from_user.id, EditorState.editor, message.chat.id)

        # ---------------------------------
        # Добавление текста
        # ---------------------------------

        @self.bot.message_handler(state=EditorState.wait, text="Добавить текст")
        def add_text_start(message: Message):
            self.bot.send_message(message.from_user.id, "Пришлите текст в формате -> <text>",
                                  reply_markup=ReplyKeyboardRemove())

            self.bot.set_state(message.from_user.id, TextAddState.TextTitle, message.chat.id)

        @self.bot.message_handler(state=TextAddState.TextTitle)
        def add_text_title(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                fsmData['textTitle'] = message.text

            self.bot.send_message(message.from_user.id,
                                  "Пришлите что хотите получать при написании этого текста!")

            self.bot.set_state(message.from_user.id, TextAddState.TextContent, message.chat.id)

        @self.bot.message_handler(state=TextAddState.TextContent, content_types=['photo', 'text'])
        def add_text_content(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                requests.post(url=f"http://localhost:8080/text/{self._username}", json={
                    "name": fsmData['textTitle'],
                    "type": message.content_type,
                    "text": message.text,
                    "image": message.photo[-1].file_id if message.photo is not None else None,
                    "caption": message.caption
                })

            self.bot.send_message(message.from_user.id, "Текст успешно добавлена!",
                                  reply_markup=ReplyKeyboardMarkup().
                                  row("Команды", "Текст").row("Выйти"))

            self.bot.set_state(message.from_user.id, EditorState.editor)

        # ---------------------------------
        # Редактирование команд
        # ---------------------------------

        def generate_commands_keyboard():
            keyboard = InlineKeyboardMarkup()

            commands_list = requests.get(f"http://localhost:8080/command/list/{self._username}").json()

            for i in commands_list:
                keyboard.row(InlineKeyboardButton(text=i, callback_data=f"text_{i}"))

            return keyboard

        @self.bot.message_handler(state=EditorState.wait, text="Редактировать команды")
        def edit_command_find(message: Message):
            msg = self.bot.send_message(message.from_user.id, "Выберите команду, которую хотите редактировать!",
                                        reply_markup=generate_commands_keyboard())

            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                fsmData['last_message'] = msg.message_id

            self.bot.set_state(message.from_user.id, CommandEditState.chooseCommand)

        @self.bot.callback_query_handler(func=lambda call: True, state=CommandEditState.chooseCommand)
        def edit_command_choose(call: CallbackQuery):
            # self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.id)
            commandData = requests.get(
                f"http://localhost:8080/command/{self._username}/{call.data.split('_')[1]}").json()
            with self.bot.retrieve_data(call.from_user.id, call.message.chat.id) as fsmData:
                fsmData['title'] = commandData['name']
            if commandData["type"] == "text":
                self.bot.send_message(call.from_user.id,
                                      f"Команда: */{commandData['name']}*\n"
                                      f"Текст: *{commandData['text']}*",
                                      reply_markup=InlineKeyboardMarkup().
                                      row(InlineKeyboardButton(text="Редактировать название команды",
                                                               callback_data=f"title_{commandData['name']}")).
                                      row(InlineKeyboardButton(text="Редактировать содержимое",
                                                               callback_data=f"content_{commandData['name']}")).
                                      row(InlineKeyboardButton(text="Удалить",
                                                               callback_data=f"delete_{commandData['name']}")).
                                      row(InlineKeyboardButton(text="Обратно",
                                                               callback_data=f"back_{commandData['name']}")),
                                      parse_mode="MarkDown")
            elif commandData['type'] == "photo":
                self.bot.send_photo(call.from_user.id, photo=commandData['image'], caption=
                f"Команда: */{commandData['name']}*\n"
                f"Текст: *{commandData['caption']}*",
                                    reply_markup=InlineKeyboardMarkup().
                                    row(InlineKeyboardButton(text="Редактировать название команды",
                                                             callback_data=f"title_{commandData['name']}")).
                                    row(InlineKeyboardButton(text="Редактировать содержимое",
                                                             callback_data=f"content_{commandData['name']}")).
                                    row(InlineKeyboardButton(text="Удалить",
                                                             callback_data=f"delete_{commandData['name']}")).
                                    row(InlineKeyboardButton(text="Обратно",
                                                             callback_data=f"back_{commandData['name']}")),
                                    parse_mode="MarkDown")

            self.bot.set_state(call.from_user.id, CommandEditState.editCommand)

        @self.bot.callback_query_handler(func=lambda call: True, state=CommandEditState.editCommand)
        def edit_command_edit(call: CallbackQuery):
            # self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
            call_data = call.data.split("_")[0]
            command_name = call.data.split("_")[1]
            msg = call.message
            if call_data == "title":
                # if call.message.content_type == "text":
                #     self.bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                #                                text="Введите новое название команды!")
                # elif call.message.content_type == "photo":
                #     self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
                msg = self.bot.send_message(chat_id=call.from_user.id, text="Введите новое название команды!")

                self.bot.set_state(call.from_user.id, CommandEditState.editTitle)

            elif call_data == "content":
                # self.bot.send_message(call.from_user.id, "Введите новое значение команды!")
                # if call.message.content_type == "text":
                #     self.bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                #                                text="Введите новое значение команды!")
                # elif call.message.content_type == "photo":
                #     self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
                msg = self.bot.send_message(call.from_user.id, "Введите новое значение команды!")

                self.bot.set_state(call.from_user.id, CommandEditState.editContent)
            elif call_data == "delete":
                code = requests.delete(f"http://localhost:8080/command/{self._username}/{command_name}").status_code

                if code == 200:
                    # if call.message.content_type == "text":
                    #     self.bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                    #                                text=f"Команда: *{command_name}* успешно удалена!",
                    #                                parse_mode="MarkDown")
                    # elif call.message.content_type == "photo":
                    #     self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
                    msg = self.bot.send_message(call.from_user.id, f"Команда: *{command_name}* успешно удалена!",
                                                parse_mode="MarkDown")

                else:
                    self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
                    # self.bot.send_message(call.from_user.id, f"Что-то пошло не так!")
                    msg = self.bot.send_message(chat_id=call.from_user.id,
                                                text="Что-то пошло не так!")

                self.bot.send_message(call.from_user.id, "Выберите команду, которую хотите редактировать!",
                                      reply_markup=generate_commands_keyboard())

                self.bot.set_state(call.from_user.id, CommandEditState.chooseCommand)

            elif call_data == "back":
                # self.bot.send_message(call.from_user.id, "Выберите команду, которую хотите редактировать!",
                #                       reply_markup=generate_commands_keyboard())
                # if call.message.content_type == "text":
                #     self.bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                #                                text="Выберите команду, которую хотите редактировать!",
                #                                reply_markup=generate_commands_keyboard())
                # elif call.message.content_type == "photo":
                #     self.bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
                self.bot.send_message(call.from_user.id, "Выберите команду, которую хотите редактировать!",
                                      reply_markup=generate_commands_keyboard())

                self.bot.set_state(call.from_user.id, CommandEditState.chooseCommand)

        @self.bot.message_handler(state=CommandEditState.editTitle)
        def edit_command_title(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                requests.put(f"http://localhost:8080/command/edit/{self._username}/{fsmData['title']}", json={
                    "name": message.text,
                })

            self.bot.send_message(message.from_user.id, "Название успешно изменено!")

            self.bot.send_message(message.from_user.id, "Выберите команду, которую хотите редактировать!",
                                  reply_markup=generate_commands_keyboard())

            self.bot.set_state(message.from_user.id, CommandEditState.chooseCommand)

        @self.bot.message_handler(state=CommandEditState.editContent, content_types=['photo', 'text'])
        def edit_command_content(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                requests.put(f"http://localhost:8080/command/edit/{self._username}/{fsmData['title']}", json={
                    "type": message.content_type,
                    "text": message.text,
                    "image": message.photo[-1].file_id if message.photo is not None else None,
                    "caption": message.caption
                })

            self.bot.send_message(message.from_user.id, "Значение успешно изменено!")

            msg = self.bot.send_message(message.from_user.id, "Выберите команду, которую хотите редактировать!",
                                        reply_markup=generate_commands_keyboard())

            self.bot.set_state(message.from_user.id, CommandEditState.chooseCommand)

        # ---------------------------------
        # Редактирование текста
        # ---------------------------------

        def generate_text_keyboard():
            keyboard = InlineKeyboardMarkup()

            text_list = requests.get(f"http://localhost:8080/text/list/{self._username}").json()

            for i in text_list:
                keyboard.row(InlineKeyboardButton(text=i, callback_data=f"text_{i}"))

            return keyboard

        @self.bot.message_handler(state=EditorState.wait, text="Редактировать текст")
        def edit_text_find(message: Message):
            self.bot.send_message(message.from_user.id, "Выберите текст, который хотите редактировать!",
                                  reply_markup=generate_text_keyboard())

            self.bot.set_state(message.from_user.id, TextEditState.chooseText)

        @self.bot.callback_query_handler(func=lambda call: True, state=TextEditState.chooseText)
        def edit_text_choose(call: CallbackQuery):
            textData = requests.get(
                f"http://localhost:8080/text/{self._username}/{call.data.split('_')[1]}").json()
            with self.bot.retrieve_data(call.from_user.id, call.message.chat.id) as fsmData:
                fsmData['title'] = textData['name']
            if textData["type"] == "text":
                self.bot.send_message(call.from_user.id,
                                      f"Текст: *{textData['name']}*\n"
                                      f"Значение: *{textData['text']}*",
                                      reply_markup=InlineKeyboardMarkup().
                                      row(InlineKeyboardButton(text="Редактировать текст",
                                                               callback_data=f"title_{textData['name']}")).
                                      row(InlineKeyboardButton(text="Редактировать содержимое",
                                                               callback_data=f"content_{textData['name']}")).
                                      row(InlineKeyboardButton(text="Удалить",
                                                               callback_data=f"delete_{textData['name']}")).
                                      row(InlineKeyboardButton(text="Обратно",
                                                               callback_data=f"back_{textData['name']}")),
                                      parse_mode="MarkDown")
            elif textData['type'] == "photo":
                self.bot.send_photo(call.from_user.id, photo=textData['image'], caption=
                f"Текст: *{textData['name']}*\n"
                f"Значение: *{textData['caption']}*",
                                    reply_markup=InlineKeyboardMarkup().
                                    row(InlineKeyboardButton(text="Редактировать текст",
                                                             callback_data=f"title_{textData['name']}")).
                                    row(InlineKeyboardButton(text="Редактировать содержимое",
                                                             callback_data=f"content_{textData['name']}")).
                                    row(InlineKeyboardButton(text="Удалить",
                                                             callback_data=f"delete_{textData['name']}")).
                                    row(InlineKeyboardButton(text="Обратно",
                                                             callback_data=f"back_{textData['name']}")),
                                    parse_mode="MarkDown")

            self.bot.set_state(call.from_user.id, TextEditState.editText)

        @self.bot.callback_query_handler(func=lambda call: True, state=TextEditState.editText)
        def edit_text_edit(call: CallbackQuery):
            call_data = call.data.split("_")[0]
            text_name = call.data.split("_")[1]
            if call_data == "title":

                self.bot.send_message(chat_id=call.from_user.id, text="Введите новое название текста!")

                self.bot.set_state(call.from_user.id, TextEditState.editTitle)

            elif call_data == "content":
                self.bot.send_message(call.from_user.id, "Введите новое значение команды!")

                self.bot.set_state(call.from_user.id, TextEditState.editContent)
            elif call_data == "delete":
                code = requests.delete(f"http://localhost:8080/text/{self._username}/{text_name}").status_code

                if code == 200:
                    self.bot.send_message(call.from_user.id, f"Текст: *{text_name}* успешно удалена!",
                                          parse_mode="MarkDown")

                else:
                    self.bot.send_message(chat_id=call.from_user.id,
                                          text="Что-то пошло не так!")

                self.bot.send_message(call.from_user.id, "Выберите текст, который хотите редактировать!",
                                      reply_markup=generate_text_keyboard())

                self.bot.set_state(call.from_user.id, TextEditState.chooseText)

            elif call_data == "back":

                self.bot.send_message(call.from_user.id, "Выберите текст, который хотите редактировать!",
                                      reply_markup=generate_text_keyboard())

                self.bot.set_state(call.from_user.id, TextEditState.chooseText)

        @self.bot.message_handler(state=TextEditState.editTitle)
        def edit_text_title(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                requests.put(f"http://localhost:8080/text/edit/{self._username}/{fsmData['title']}", json={
                    "name": message.text,
                })

            self.bot.send_message(message.from_user.id, "Название успешно изменено!")

            self.bot.send_message(message.from_user.id, "Выберите текст, который хотите редактировать!",
                                  reply_markup=generate_text_keyboard())

            self.bot.set_state(message.from_user.id, TextEditState.chooseText)

        @self.bot.message_handler(state=TextEditState.editContent, content_types=['photo', 'text'])
        def edit_text_content(message: Message):
            with self.bot.retrieve_data(message.from_user.id, message.chat.id) as fsmData:
                requests.put(f"http://localhost:8080/text/edit/{self._username}/{fsmData['title']}", json={
                    "type": message.content_type,
                    "text": message.text,
                    "image": message.photo[-1].file_id if message.photo is not None else None,
                    "caption": message.caption
                })

            self.bot.send_message(message.from_user.id, "Значение успешно изменено!")

            self.bot.send_message(message.from_user.id, "Выберите текст, который хотите редактировать!",
                                  reply_markup=generate_text_keyboard())

            self.bot.set_state(message.from_user.id, TextEditState.chooseText)

        @self.bot.message_handler(state=EditorState.wait)
        def wait_continue(message: Message):
            self.bot.set_state(message.from_user.id, EditorState.wait)

        # ---------------------------------
        # Основная логика бота
        # ---------------------------------

        @self.bot.message_handler(content_types=['text', 'photo', 'audio', 'document', 'sticker', 'video',
                                                 'video_note', 'voice', 'contact', 'location', 'venue', 'animation'],
                                  state=None)
        def handler(message: Message):
            print(self.bot.get_state(message.from_user.id))
            requests.post(url=f"http://localhost:8080/message?userId={message.from_user.id}", json={
                "message_id": message.message_id,
                "content_type": message.content_type,
                "date": message.date,
                "text": message.text,
                "audio": message.audio.file_id if message.audio is not None else None,
                "document": message.document.file_id if message.document is not None else None,
                "photo": message.photo[-1].file_id if message.photo is not None else None,
                "sticker": message.sticker.file_id if message.sticker is not None else None,
                "video": message.video.file_id if message.video is not None else None,
                "videoNote": message.video_note.file_id if message.video_note is not None else None,
                "voice": message.voice.file_id if message.voice is not None else None,
                "caption": message.caption,
                "contact": message.contact,
                "location": message.location.to_json() if message.location is not None else None,
                "venue": message.venue,
                "animation": message.animation.file_id if message.animation is not None else None
            })
            admin = requests.get(
                f"http://localhost:8080/user/admin/{self._username}?UserId={message.from_user.id}").json()

            if message.content_type == "text":
                self.logger.info(f'{message.from_user.id} - {message.text}')
                if message.text.startswith("/"):
                    command = message.text.split("/")[1]
                    if command == "docs":
                        # get_web(set_list(self._username))
                        self.bot.send_document(message.from_user.id, open(f"{self._username}.html", 'rb'))
                        return

                    message_context = requests.get(f"http://localhost:8080/command/{self._username}/{command}")
                    if message_context.status_code == 200:
                        message_context = message_context.json()
                        if message_context["type"] == "photo":
                            self.bot.send_photo(message.from_user.id, photo=message_context["image"],
                                                caption=message_context["caption"])
                        elif message_context["type"] == "text":
                            self.bot.send_message(message.chat.id,
                                                  f'{message_context["text"]}')
                    else:
                        self.bot.send_message(message.chat.id, "Такой команды нет!")
                    return

                if message.text == "Редактор" and admin:
                    self.bot.send_message(message.from_user.id, "Выберите что нужно сделать!\n\n"
                                                                "🔸 Добавить команду\n"
                                                                "🔸 Добавить текст",
                                          reply_markup=ReplyKeyboardMarkup().
                                          row("Команды", "Текст").row("Выйти"))

                    # self.bot.register_next_step_handler(msg, editing)
                    self.bot.set_state(message.from_user.id, EditorState.editor, message.chat.id)

                    return

                context = requests.get(f"http://localhost:8080/text/{self._username}/{message.text}")
                if context.status_code == 200:
                    message_context = context.json()
                    if message_context["type"] == "text":
                        self.bot.send_message(message.from_user.id, text=message_context["text"])
                    elif message_context["type"] == "photo":
                        self.bot.send_photo(message.from_user.id, photo=message_context["image"],
                                            caption=message_context["caption"])
                else:
                    # if self.data["chatgpt"]:
                    msg = self.bot.send_message(message.from_user.id, "Думаю...")
                    self.bot.send_chat_action(message.from_user.id, "typing")

                    try:
                        completion = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "user", "content": f"{message.text}"}
                            ]
                        )

                        # self.bot.send_message(message.from_user.)

                        self.bot.delete_message(message.from_user.id, message_id=msg.id)

                        self.bot.send_message(message.from_user.id, f"```\n{message.text}\n```"
                                                                    f"\n{completion.choices[0].message.content}",
                                              'Markdown')
                    except openai.error.RateLimitError as e:
                        print(e)
                        self.bot.delete_message(message.from_user.id, message_id=msg.id)

                        self.bot.send_message(message.from_user.id,
                                              "Бот сейчас слишком сильно загружен, повтори попытку через минуту!")
                # else:
                #     self.bot.send_message(message.from_user.id, "Такой команды нет!")
            elif message.content_type == "voice":
                pass

        print(f">> [{self._username}] - START WORKING")
        asyncio.run(self.bot.infinity_polling(timeout=10, long_polling_timeout=5))


if __name__ == '__main__':
    Bots = {}

    while True:
        add_info = check_bots()

        Bots[add_info[0]] = add_info[1]
        Bots[add_info[0]].start()
