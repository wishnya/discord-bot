from discord.ext import commands
import discord
import random
import os
import requests

description = '''Test python bot.'''
bot = discord.Client()

@bot.event
async def on_ready():
    print('UP!')



currentQuestion = False
currentAnswer = False

arr = ', '.join([
    'cat',
    'wiki',
    'python',
    'quiz',
    'ask'
])

async def cat(msg):
    gif = requests.get('http://thecatapi.com/api/images/get').url
    await bot.send_message(msg.channel, gif)

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

async def quiz(msg):
    if not currentQuestion:
        setQuestion()
        await bot.send_message(msg.channel, "А теперь вопрос: {}".format(currentQuestion))
    else:
        await bot.send_message(msg.channel, currentQuestion)

async def ask(msg):
    answer = msg.content.split(' ')
    answer.pop(0)
    if len(answer) > 1:
        await bot.send_message(msg.channel, 'Ответ состоит из одного слова.')
    elif not len(answer):
        await bot.send_message(msg.channel, '{}, Вы не указали ответ.'.format(msg.author.name))
    else:
        global currentAnswer
        if answer[0].lower() == currentAnswer:
            await bot.send_message(msg.channel, 'Это правильный ответ!')
            # global currentQuestion
            setQuestion()
            await bot.send_message(msg.channel, 'А теперь новый вопрос: {}'.format(currentQuestion))
        else:
            await bot.send_message(msg.channel, 'К сожелению, это неправильный ответ.')


def setQuestion():
    global currentQuestion
    global currentAnswer
    file = open(os.path.dirname(os.path.abspath(__file__)) + os.sep + 'questions.txt', 'r', encoding='utf-8')
    text = file.readlines()
    countLines = len(text)
    numLine = random.randrange(countLines)
    line = text[numLine].rstrip().split('|')
    currentQuestion = line[0]
    currentAnswer = line[1]



@bot.event
async def on_message(msg):
    if bot.user.id != msg.author.id:
        if msg.content.startswith('!list'):
            await bot.send_message(msg.channel, arr)

        elif msg.content.startswith('!cat'):
            await cat(msg)

        elif msg.content.startswith('!wiki'):
            await search(msg, 'wiki')

        elif msg.content.startswith('!python'):
            await search(msg, 'python')

        elif msg.content.startswith('!quiz'):
            await quiz(msg)

        elif msg.content.startswith('!ask'):
            await ask(msg)


bot.run('MzI0MjU1MDEzNTk5NzA3MTM2.DChAsQ.XnWQTHUNPfe37YIB1-MsxI58fkM')
