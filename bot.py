from discord.ext import commands
import random
import os
import requests

currentQuestion = False
currentAnswer = False

description = '''Test python bot.'''
bot = commands.Bot(command_prefix='!', description=description)

def setQuestion():
    global currentQuestion
    global currentAnswer
    file = open(os.path.dirname(os.path.abspath(__file__)) + '\questions.txt', 'r', encoding='utf-8')
    text = file.readlines()
    countLines = len(text)
    numLine = random.randrange(countLines)
    line = text[numLine].rstrip().split('|')
    currentQuestion = line[0]
    currentAnswer = line[1]
    
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def wiki(article: str):
    await bot.say('https://ru.wikipedia.org/wiki/{}'.format(article))

@bot.command()
async def python(version: int, tag: str):
    await bot.say('https://docs.python.org/{0}/search.html?q={1}'.format(version, tag))

@bot.command()
async def quiz():
    global currentQuestion
    global currentAnswer
    if not currentQuestion:
        setQuestion()
        await bot.say("А теперь вопрос: {}".format(currentQuestion))
    else:
        await bot.say(currentQuestion)

@bot.command()
async def ask(answer: str):
    global currentAnswer
    if answer.lower() == currentAnswer:
        await bot.say('Это правильный ответ!')
        global currentQuestion
        setQuestion()
        await bot.say('А теперь новый вопрос: {}'.format(currentQuestion))
    else:
        await bot.say('К сожелению, это неправильный ответ.')



bot.run('MzI0MjU1MDEzNTk5NzA3MTM2.DCWzsA.W-NXPNw3IQP_7gsWlNRiZ_5ebcg')
