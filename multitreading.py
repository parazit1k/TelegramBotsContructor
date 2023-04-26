import asyncio
from threading import *
from typing import TextIO

import openai
import telebot
from html2image import Html2Image
from jinja2 import Environment, FileSystemLoader
from telebot.types import *

hti = Html2Image()

openai.api_key = "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"
to_run = ['paradickmabot', 'SoundHuntersBot']


def check_bots():
    while True:
        if len(to_run) == 0:
            file = input()
        else:
            file = to_run[0]
            del to_run[0]

        with open(f"{file}.json", 'r') as f:
            data = json.load(f)

            return Thread(target=Bot, args=(data['token'], data,))


def set_list(name: str):
    result = [["Команды / текст", "Значения"]]

    with open(f"{name}.json") as f:
        json_file = json.load(f)

        result.append(["/start", json_file["start"]])
        result.append(["/help", json_file["help"]])
        for i, v in json_file["commands"].items():
            if v["type"] == "message":
                result.append([f"/{i}", v["text"][:25]])
            elif v["type"] == "photo":
                result.append([f"/{i}", f'<a href="{v["img"]}">photo</a><br />', v["caption"][:25]])

        for i, v in json_file["text"].items():
            result.append([i, v[:25]])

        result.append(["chatgpt", json_file["chatgpt"]])

    return result, name


def get_web(tpl: tuple) -> TextIO:
    env = Environment(loader=FileSystemLoader('templates'))

    template = env.get_template('test.html')

    rendered_template = template.render(nested_list=tpl[0])

    with open(f'{tpl[1]}.html', 'w') as f:
        f.write(rendered_template)

        return f


get_web(set_list('paradickmabot'))
get_web(set_list('SoundHuntersBot'))


class Bot:

    def __init__(self, token, data):
        self.bot = telebot.TeleBot(token)

        self._username = self.bot.get_me().username

        self.handler = logging.FileHandler(f"{self._username}.log")
        self.handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))

        self.logger = logging.getLogger(self._username)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

        self.data = data

        @self.bot.message_handler(commands=['start'])
        def start(message: Message):
            self.logger.info(f'{message.from_user.id} - {message.text}')
            self.bot.send_message(message.chat.id, self.data['start'])

        @self.bot.message_handler()
        def handler(message: Message):
            print(message)
            if message.content_type == "text":
                self.logger.info(f'{message.from_user.id} - {message.text}')
                if message.text[0] == "/":
                    if message.text.split("/")[1] == "docs":
                        get_web(set_list(self._username))
                        self.bot.send_document(message.from_user.id, open(f"{self._username}.html", 'rb'))
                        return
                    if message.text.split("/")[1].split(" ")[0] in self.data['commands'].keys():
                        if self.data["commands"][message.text.split("/")[1].split(" ")[0]]["type"] == "photo":
                            self.bot.send_photo(message.from_user.id, photo=self.data["commands"]
                            [message.text.split("/")[1].split(" ")[0]]["img"],
                                                caption=
                                                self.data["commands"][message.text.split("/")[1].split(" ")[0]][
                                                    "caption"])
                        elif self.data["commands"][message.text.split("/")[1].split(" ")[0]]['type'] == "message":
                            self.bot.send_message(message.chat.id,
                                                  f'{self.data["commands"][message.text.split("/")[1].split(" ")[0]]["text"]}')
                    else:
                        self.bot.send_message(message.chat.id, "Такой команды нет!")
                elif message.text in self.data['text'].keys():
                    self.bot.send_message(message.from_user.id, self.data["text"][message.text])
                else:
                    if self.data["chatgpt"]:
                        msg = self.bot.send_message(message.from_user.id, "Думаю...")
                        self.bot.send_chat_action(message.from_user.id, "typing")

                        try:
                            completion = openai.ChatCompletion.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "user", "content": f"{message.text}"}
                                ]
                            )
                            self.bot.delete_message(message.from_user.id, message_id=msg.id)

                            self.bot.send_message(message.from_user.id, f"```\n{message.text}\n```"
                                                                        f"\n{completion.choices[0].message.content}",
                                                  'Markdown')
                        except openai.error.RateLimitError:
                            self.bot.delete_message(message.from_user.id, message_id=msg.id)

                            self.bot.send_message(message.from_user.id,
                                                  "Бот сейчас слишком сильно загружен, повтори попытку через минуту!")
                    else:
                        self.bot.send_message(message.from_user.id, "Такой команды нет!")

        print(f"[{self._username}] - START WORKING")
        asyncio.run(self.bot.infinity_polling())


if __name__ == '__main__':
    Bots = []

    while True:
        Bots.append(check_bots())
        Bots[-1].start()
