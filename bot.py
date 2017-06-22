import discord
import random
import os
import requests
import sqlite3
import psycopg2
import urllib.parse as urlparse

bot = discord.Client()


@bot.event
async def on_ready():
    print('UP!')


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
cursor.execute('CREATE TABLE IF NOT EXISTS quiz ('
              'question TEXT,'
              'ask TEXT)')

cursor.execute('CREATE TABLE IF NOT EXISTS scopes ('
              'id INT,'
              'scope INT DEFAULT 0)')



# Перменные, содержащие вопрос и ответ.
currentQuestion = False
currentAnswer = False

# Массив с доступными командами
commands = ', '.join([
    'cat',
    'wiki',
    'python',
    'quiz',
    'ask'
])
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
    if not currentQuestion:
        setQuestion()
        await bot.send_message(msg.channel, "А теперь вопрос: {}".format(currentQuestion))
    else:
        await bot.send_message(msg.channel, currentQuestion)


# Фукция принимающая ответ на текущий вопрос
async def ask(msg):
    answer = msg.content.split(' ')
    answer.pop(0)
    if len(answer) > 1:
        await bot.send_message(msg.channel, '{}, ответ состоит из одного слова.'.format(msg.author.mention))
    elif not len(answer):
        await bot.send_message(msg.channel, '{}, Вы не указали ответ.'.format(msg.author.mention))
    else:
        global currentAnswer
        if answer[0].lower() == currentAnswer:
            usrScope = 0
            id = msg.author.id
            cursor = dbase.cursor()
            cursor.execute('SELECT scope FROM scopes WHERE id = ?', [id])
            scope = cursor.fetchone()
            if scope is None:
                usrScope = 1
                cursor.execute('INSERT INTO scopes (id, scope) VALUES(?, ?)', (id, usrScope))
            else:
                usrScope = scope[0] + 1
                cursor.execute('UPDATE scopes SET scope = ? WHERE id = ?', (usrScope, id))
            dbase.commit()
            cursor.close()
            setQuestion()
            await bot.send_message(msg.channel, '{} правильно ответил(а) на вопрос и получаете 1 балл.\n'
                                                'Теперь количество ваших баллов равняется {}.'.format(
                msg.author.mention, usrScope))
            await bot.send_message(msg.channel, 'А теперь новый вопрос: {}'.format(currentQuestion))
        else:
            await bot.send_message(msg.channel, '{}, к сожалению это неправильный ответ.'.format(msg.author.mention))


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
def setQuestion(qst='update'):
    cursor = dbase.cursor()
    questions = {
        'insert': 'INSERT INTO quiz(question, ask) VALUES(?, ?)',
        'update': 'UPDATE quiz SET question = ?, ask = ? WHERE question = ?'
    }
    global currentQuestion
    global currentAnswer
    file = open(os.path.dirname(os.path.abspath(__file__)) + os.sep + 'questions.txt', 'r', encoding='utf-8')
    text = file.readlines()
    countLines = len(text)
    numLine = random.randrange(countLines)
    line = text[numLine].rstrip().split('|')
    if qst == 'update':
        line.append(currentQuestion)
    cursor.execute(questions[qst], line)
    currentQuestion = line[0]
    currentAnswer = line[1]
    dbase.commit()
    cursor.close()


# Функция обработки команд в чате.
@bot.event
async def on_message(msg):
    if bot.user.id != msg.author.id:
        if msg.content.startswith('!list'):
            await bot.send_message(msg.channel, commands)

        elif msg.content.startswith('!cat'):
            await cat(msg)

        elif msg.content.startswith('!wiki'):
            await search(msg, 'wiki')

        elif msg.content.startswith('!python'):
            await search(msg, 'python')

        elif msg.content.startswith('!quiz'):
            await bot.send_message(msg.channel, currentQuestion)

        elif msg.content.startswith('!ask'):
            await ask(msg)

        elif msg.content.startswith('!top'):
            await top(msg)


if __name__ == '__main__':
    # Отправка запроса для получения вопроса и ответа в базе данных. Если они(вопрос и ответ) есть,
    # то записываются в соотвествующие переменные, если нет - запускается функция setQuestion,
    # берущая случайный вопрос и ответ из текстового файл и добавляет их в базу
    cursor.execute('SELECT question, ask FROM quiz')
    quizData = cursor.fetchall()
    if quizData:
        currentQuestion = quizData[0][0]
        currentAnswer = quizData[0][1]
        cursor.close()
    else:
        setQuestion('insert')

    # Запуск бота
    bot.run('MzI0MjU1MDEzNTk5NzA3MTM2.DCw-CA.aOHfh4nBQOqY-lCI2fYevvlkxug')
