import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import asyncio
import datetime
import urllib3

description = """a GGI news feed bot"""
# https://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C

client = discord.Client()
#bot = commands.Bot(command_prefix='!', description=description)
token = "MzU3MTY5NTA5MzM4OTcyMTYx.DJl_ig.IBYtxryOuYyVHfl2ahXgfj6Nwt0"

news_list = []

class news_item():
    def __init__(self, headline, link, date):
        self.headline = headline
        self.link = link
        self.date = date

    def __eq__(self, other):
        return self.date == other.date

    headline = ""
    date = ""
    link = ""

async def get_news():
    await client.wait_until_ready()
    #channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        # scrape stockwatch for news, check if "new" and if so, post
        h = urllib3.PoolManager()
        url = 'http://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C'
        r = h.request('GET', url)
        soup = BeautifulSoup(r.data, 'lxml')
        table = soup.find(id="MainContent_NewsList1_Table1_Table1")
        rows = table("tr")[1:] # skip header
        for tr in rows:
            cols = tr("td")  # Equiv to .findAll("td")
     
            headline = cols[5].string.strip()
            link = 'http://www.stockwatch.com' + cols[5].a.get('href')
            date = cols[0].string.strip()

            news = news_item(headline, link, date)
            if news not in news_list:
                news_list.append(news)
                await client.send_message(channel, '{} - {} ({})'.format(date, headline, link))
        
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('-------')

@client.event
async def on_message(message):
    if message.content.startswith('.news'):
        print("Printing 5 most recent news releases for {} ({})".format(message.author.nick, message.author))
        output = ""
        for nr in news_list[:5]:
            # post the most recent 5 items
            output += '{} - {} ({})\n'.format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.latest'):
        nr = news_list[0]
        print("Printing most recent news release for {} ({})".format(message.author.nick, message.author))
        await client.send_message(message.channel, "{} - {}({})".format(nr.date, nr.headline, nr.link))


client.loop.create_task(get_news())
client.run(token)