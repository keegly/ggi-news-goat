import asyncio
import discord
from bs4 import BeautifulSoup
import aiohttp
#import logging

description = """a GGI news feed bot"""
# https://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C

client = discord.Client()
# spammy?
#logging.basicConfig(level=logging.INFO)
#bot = commands.Bot(command_prefix='!', description=description)
token = "MzU3MTY5NTA5MzM4OTcyMTYx.DJl_ig.IBYtxryOuYyVHfl2ahXgfj6Nwt0"

news_list = []
halt_list = []

class news_item():
    def __init__(self, headline, link, date, time):
        self.headline = headline
        self.link = link
        self.date = date
        self.time = time

    def __eq__(self, other):
        return self.date == other.date and self.time == other.time and self.headline == other.headline

    headline = ""
    date = ""
    time = ""
    link = ""

class halt_item():
    def __init__(self, text, link, date):
        self.date = date
        self.text = text
        self.link = link

    def __eq__(self, other):
        return self.date == other.date and self.text == other.text

    date = ""
    text = ""
    link = ""

async def get_news():
    await client.wait_until_ready()
    #channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        # scrape stockwatch for news, check if "new" and if so, post
        #url = 'http://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C'
        # SEDI faster?
        url = 'http://www.sedar.com/new_docs/new_press_releases_en.htm'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                print("HTTP Request returned status {}".format(r.status))
                if r.status != 200:
                    print("HTTP Request failed, sleeping.")
                elif r.status == 200:
                    soup = BeautifulSoup(await r.text(), 'lxml')
                    table = soup.find_all("table")[1]
                    rows = table("tr")[1:] # skip table header
                    counter = 0
                    for tr in rows:                        
                            cols = tr("td")  # Equiv to .findAll("td")
                            #Garibaldi Resources Corp.
                            if cols[0].text is None:
                                    continue
                            elif "Garibaldi Resources" in cols[0].text.strip():
                                    name = cols[0].text.strip()
                                    while True:
                                            # check for invalid row ie we got all the news
                                            temp = rows[counter + 1]("td")
                                            if len(temp) is 1:
                                                    break # finished
                                            
                                            date = temp[1].text.strip()
                                            time = temp[2].text.strip()
                                            headline = temp[3].text.strip() #News Release - English
                                            #www.sedar.com/GetFile.do?lang=EN + link
                                            link = 'http://www.sedar.com/GetFile.do?lang=EN' + temp[3].a.get('title')
                                            
                                            news = news_item(headline, link, date, time)
                                            if news not in news_list:
                                                news_list.append(news)
                                                print("Found new {} SEDAR release!!".format(name))
                                                output = '{} {} > {} > {} ({})'.format(date, time, name, headline, link)
                                                await client.send_message(channel, output)
                                            else:
                                                print("skipping old news item")

                                            counter += 1
                                    break                     
                            counter += 1
                    print("No GGI updates found, sleeping.")
        await asyncio.sleep(30)

async def get_halted():
    await client.wait_until_ready()
    #channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action

    while not client.is_closed:
        url = 'http://iiroc.mediaroom.com'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                print("HTTP Request returned status {}".format(r.status))
                if r.status != 200:
                    print("HTTP Request failed.")
                elif r.status == 200:
                    soup = BeautifulSoup(await r.text(), 'lxml')
                    res = soup.find_all('div', {"class" : "item"})
                    for item in res:
                        date = item.contents[1].string.strip()
                        text = item.contents[2].string.strip()
                        link = item.contents[2].a.get("href")

                        if 'GGI' in text:
                            halt = halt_item(text, link, date)
                            if halt not in halt_list:                                
                                halt_list.append(halt)
                                print("Found new GGI Halt notice")
                                output = '{} > {} ({})'.format(date, text, link)
                                await client.send_message(channel, output)
                            else:
                                print("Skipping old halt item")
                            
        print("Halt search complete, sleeping")
        await asyncio.sleep(32)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('-------')
    await client.change_presence(game=discord.Game(name='Shit Just Goat Real'))

@client.event
async def on_message(message):
    if message.content.startswith('.news'):
        print("Command .news received from {} ({})".format(message.author, message.author.nick))
        output = ""
        if len(news_list) is 0:
            output = "No recent news for GGI."
        for nr in news_list[:5]:
            # post the most recent 5 items
            output += '{} - {} ({})\n'.format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.latest'):
        output = ""
        print("Command .latest received from {} ({})".format(message.author, message.author.nick))
        if len(news_list) is 0:
            output = "No recent news for GGI"
        else:
            nr = news_list[0]
            output = "{} - {}({})".format(nr.date, nr.headline, nr.link)
            print("Printing most recent news release for {} ({})".format(message.author.nick, message.author))
        await client.send_message(message.channel, output)

    elif message.content.startswith('.clap'):
        if message.author.id == '357169509338972161': #ignore own comments
            return

        print("Command .clap received from {} ({})".format(message.author, message.author.nick))
        output = message.content
        output = output.replace(".clap", "")
        words = output.split()
        output = "👏"
        tmp = await client.send_message(message.channel, output)
        for word in words:
            output += word
            output += "👏"
            await client.edit_message(tmp, output)
            asyncio.sleep(0.5)

client.loop.create_task(get_news())
client.loop.create_task(get_halted())
client.run(token)