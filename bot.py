import discord
import random
import os
import requests
import psycopg2
import urllib.parse as urlparse
from asyncio import sleep

bot = discord.Client()

@bot.event
async def on_ready():
    print('Bot UP!')


# Открытие/создание базы данных, добавдение таблиц, если их нет.
urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])
dbase = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
cursor = dbase.cursor()

cursor.execute('CREATE TABLE IF NOT EXISTS scopes ('
              'id BIGINT,'
              'scope INT DEFAULT 0)')

# Переменные, содержащие вопрос и ответ.
# Перменные, содержащие вопрос и ответ.
channelsQuestions = {}

# Timer
timer = False

# Время на один вопрос
timeOnAsk = 20

# Сигнал на остановку викторины
stopSignal = False

# Массив с доступными командами
commands = '\n'.join([
    '!top -  вывести топ-10 местных эрудитов.',
    '!cat - вывести изображение няшного кисика.:smirk_cat:',
    '!wiki <запрос> -  поиск по википедии(можно сразу несколько искомых слов через пробел).',
    '!python <запрос> - поиск по документации Python 3(можно сразу несколько искомых слов через пробел).',
    '!в (на русской раскладке) - вывести вопрос викторины.',
    'Ответ принимается без дополнительных команд и состоит из одного слова.'
])

# Массив с эможи в качестве обозначения места в викторине.
places = [
    ':first_place:',
    ':second_place:',
    ':third_place:',
    ':four:',
    ':five:',
    ':six:',
    ':seven:',
    ':eight',
    ':nine:',
    ':ten:'
]

# Функция, отправляющая случайное изображение кошек
async def cat(msg):
    gif = requests.get('http://thecatapi.com/api/images/get').url
    await bot.send_message(msg.channel, gif)

# Функция поиска по сайтам.
async def search(msg, where):
    places = {
        'python': 'https://docs.python.org/3/search.html?q={}',
        'wiki': 'https://wikipedia.org/wiki/{}'
    }
    quest = msg.content.split(' ')
    quest.pop(0)
    if len(quest) == 1:
        quest = places[where].format(quest[0].lower())
        await bot.send_message(msg.channel, quest)
    elif len(quest) > 1:
        for i in quest:
            i = places[where].format(i.lower())
            await bot.send_message(msg.channel, i)
    else:
        quest = 'Вы не указали искомое.'
        await bot.send_message(msg.channel, quest)

# Функция, посылающая вопрос в чат
async def quiz(msg):
    chl = msg.channel.name
    if chl not in channelsQuestions:

        channelsQuestions[chl] = [False, False]
    if channelsQuestions[chl][0]:
        await bot.send_message(msg.channel, channelsQuestions[chl][0])
    else:
        global timer
        global stopSignal
        count = 1
        textlist = msg.content.split(' ')
        if msg.channel.name == 'quiz':
            if len(textlist) == 2:
                try:
                    count = int(textlist[1])
                    stopSignal = True
                except ValueError:
                    count = 0
        else:
            if len(textlist) != 1:
                count = 0
            else:
                stopSignal = True

        for i in range(count):
            if stopSignal:
                setQuestion(channelsQuestions[chl])
                timer = bot.loop.call_later(timeOnAsk, bot.loop.create_task, noAsk(msg))
                await bot.send_message(msg.channel, channelsQuestions[chl][0])
                await openSymbol(msg)

        stopSignal = False

# Фукция принимающая ответ на текущий вопрос
async def ask(msg):
    if not channelsQuestions[msg.channel.name][1]:
        await bot.send_message(msg.channel, "Вопрос еще не был установлен. Для установки вопроса воспользуйтесь командой"
                                            " '!quiz'.")
    else:
        answer = msg.content.split()
        if answer[0].lower() == channelsQuestions[msg.channel.name][1]:
            global timer
            timer.cancel()
            timer = None
            id = msg.author.id
            cursor = dbase.cursor()
            cursor.execute('SELECT scope FROM scopes WHERE id = {}'.format(id))
            scope = cursor.fetchone()
            if scope is None:
                usrScope = 1
                cursor.execute('INSERT INTO scopes (id, scope) VALUES({}, {})'.format(id, usrScope))
            else:
                usrScope = scope[0] + 1
                cursor.execute('UPDATE scopes SET scope = {} WHERE id = {}'.format(usrScope, id))
            dbase.commit()
            cursor.close()
            await bot.send_message(msg.channel, '{} правильно ответил(а) на вопрос и получаете 1 балл.\n'
                                                'Теперь количество ваших очков равняется {}.'.format(msg.author.mention,
                                                                                                     usrScope))
            channelsQuestions[msg.channel.name][0] = False
            channelsQuestions[msg.channel.name][1] = False
        else:
            await bot.send_message(msg.channel, '{}, к сожалению это неправильный ответ.'.format(msg.author.mention))

# Функция, действующая в том случае, если не было правильного ответа
async def noAsk(msg):
    await bot.send_message(msg.channel, "К сожалению, никто не назвал правильный ответ."
                                        "\nПравильным ответом было слово '{}'".format(channelsQuestions[msg.channel.name][1]))
    channelsQuestions[msg.channel.name][0] = False
    channelsQuestions[msg.channel.name][1] = False

# Открытие букв в слове, являющимся ответом на вопрос
async def openSymbol(msg):
    lenght = len(channelsQuestions[msg.channel.name][1])
    part = round(lenght / 3)
    timeOpenSymbol = timeOnAsk / 3
    for i in range(part + 1):
        if channelsQuestions[msg.channel.name][1]:
            await bot.send_message(msg.channel,
                                   channelsQuestions[msg.channel.name][1][:i * part] + (lenght - (i * part)) * '-')
            await sleep(timeOpenSymbol)

# Список из 10 лидеров викторины
async def top(msg):
    cursor = dbase.cursor()
    cursor.execute('SELECT id, scope FROM scopes ORDER BY scope DESC LIMIT 30')
    leaders = cursor.fetchall()
    count = 0
    result = {}
    for leader in leaders:
        usr = str(leader[0])
        scope = leader[1]
        if count == 0:
            result[scope] = [usr]
        else:
            if scope in result:
                result[scope].append(usr)
            else:
                result[scope] = [usr]
        count += 1


    count = 0

    for key in result:
        if count != len(result):
            nick = []
            if len(result[key]) > 1:
                for id in result[key]:
                    tmp = discord.utils.get(msg.server.members, id=id)
                    if tmp is not None:
                        nick.append(tmp.name)
            else:
                tmp = discord.utils.get(msg.server.members, id=result[key][0])
                if tmp is not None:
                    nick.append(tmp.name)
            scope = key
            if nick:
                nick = ', '.join(nick)
                await bot.send_message(msg.channel, '{} {}: {} балл(ов).'.format(places[count], nick, scope))
                count += 1
    cursor.close()

# Функция, которая выбирает случайный вопрос и ответ из текстового файла, а затем записывает выбранное
# в базу данных и переменные для вопроса и ответа.
def setQuestion(place):
    file = open(os.path.dirname(os.path.abspath(__file__)) + os.sep + 'questions.txt', 'r', encoding='utf-8')
    text = file.readlines()
    countLines = len(text)
    numLine = random.randrange(countLines)
    line = text[numLine].rstrip().split('|')
    place[0], place[1] = line[0], line[1]
    print(place[1])

# Функция обработки команд в чате.
@bot.event
async def on_message(msg):
    if bot.user.id != msg.author.id:
        text = msg.content.split(' ')[0]
        if text == '!help':
            await bot.send_message(msg.channel, commands)

        elif text == '!cat':
            await cat(msg)

        elif text == '!wiki':
            await search(msg, 'wiki')

        elif text == '!python':
            await search(msg, 'python')

        elif text == '!в':
            await quiz(msg)

        elif msg.channel.name == 'quiz' and text == '!stop':
            global stopSignal
            stopSignal = False

        elif text == '!top':
            await top(msg)

        elif not msg.author.bot and channelsQuestions[msg.channel.name][1] and len(msg.content.split()) == 1:
            await ask(msg)

# Запуск бота
bot.run('MzI0MjU1MDEzNTk5NzA3MTM2.DCw-CA.aOHfh4nBQOqY-lCI2fYevvlkxug')
