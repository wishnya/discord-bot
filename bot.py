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
currentQuestion = False
currentAnswer = False

# Timer
timer = False

# Массив с доступными командами
commands = '\n'.join([
    'Чтобы вывести топ-10 местных эрудитов, иожно воспользоваться командой "!top".',
    'Чтобы вывести изображение няшного кисика, используйте команду "!cat".',
    'Чтобы осуществить поиск по википедии, используйте команду "!wiki ", а затем искомое(можно сразу несколько искомых слов через пробел).'
    'Практически точно так же работает поиск по документации python 3 версии, но с помощью команды "!python".',
    'Для того, вывести вопрос викторины, используйте команду "!в" на русской раскладке.'
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
    if currentQuestion:
        await bot.send_message(msg.channel, currentQuestion)
    else:
        global timer
        setQuestion()
        loop = bot.loop
        timer = loop.call_later(60, loop.create_task, noAsk(msg))
        await bot.send_message(msg.channel, currentQuestion)
        await openSymbol(msg)

# Фукция принимающая ответ на текущий вопрос
async def ask(msg):
    global currentAnswer
    if not currentAnswer:
        await bot.send_message(msg.channel,
                               "Вопрос еще не был установлен. Для установки вопроса воспользуйтесь командой"
                               " '!в'.")
    else:
        answer = msg.content.split()
        if answer[0].lower() == currentAnswer:
            global currentQuestion
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
            currentAnswer = False
            currentQuestion = False
            await bot.send_message(msg.channel, '{} правильно ответил(а) на вопрос и получаете 1 балл.\n'
                                                'Теперь количество ваших баллов равняется {}.'.format(
                msg.author.mention, usrScope))

# Функция, действующая в том случае, если не было правильного ответа
async def noAsk(msg):
    global currentAnswer
    global currentQuestion
    await bot.send_message(msg.channel, "К сожалению, никто не назвал правильный ответ."
                                        "\nПравильным ответом было слово '{}'.".format(currentAnswer))
    currentQuestion = False
    currentAnswer = False

# Открытие букв в слове, являющимся ответом на вопрос
async def openSymbol(msg):
    global currentAnswer
    lenght = len(currentAnswer)
    timeOpenSymbol = 60 / lenght
    for i in range(lenght):
        if currentAnswer:
            await bot.send_message(msg.channel, currentAnswer[:i] + ((lenght - i) * '-'))
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
def setQuestion():
    global currentQuestion
    global currentAnswer
    cursor = dbase.cursor()
    file = open(os.path.dirname(os.path.abspath(__file__)) + os.sep + 'questions.txt', 'r', encoding='utf-8')
    text = file.readlines()
    countLines = len(text)
    numLine = random.randrange(countLines)
    line = text[numLine].rstrip().split('|')
    cursor.execute('''INSERT INTO quiz (question, ask) VALUES('{}', '{}')'''.format(*line))
    currentQuestion = line[0]
    currentAnswer = line[1]
    dbase.commit()
    cursor.close()

# Функция обработки команд в чате.
@bot.event
async def on_message(msg):
    if bot.user.id != msg.author.id:
        if msg.content.startswith('!help'):
            await bot.send_message(msg.channel, commands)

        elif msg.content.startswith('!cat'):
            await cat(msg)

        elif msg.content.startswith('!wiki'):
            await search(msg, 'wiki')

        elif msg.content.startswith('!python'):
            await search(msg, 'python')

        elif msg.content.startswith('!в'):
            await quiz(msg)

        elif not msg.author.bot and currentAnswer and len(msg.content.split()) == 1:
            await ask(msg)

        elif msg.content.startswith('!top'):
            await top(msg)

# Запуск бота
bot.run('MzI0MjU1MDEzNTk5NzA3MTM2.DCw-CA.aOHfh4nBQOqY-lCI2fYevvlkxug')
