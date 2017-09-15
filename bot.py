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

async def get_news():
    await client.wait_until_ready()
    channel = discord.Object(id='355892436888715279') # test server
    #channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        # scrape stockwatch for news, check if "new" and if so, post
        h = urllib3.PoolManager()
        #url = 'http://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C'
        url = 'http://www.sedar.com/new_docs/new_press_releases_en.htm'
        r = h.request('GET', url)
        soup = BeautifulSoup(r.data, 'lxml')
        table = soup.find_all("table")[1]
      #  print(table)
        rows = table("tr")[1:] # skip header
        counter = 0
        for tr in rows:                        
                cols = tr("td")  # Equiv to .findAll("td")
               # print (cols)
                #Garibaldi Resources Corp.
                #Achieve Life Sciences, Inc. 
                #Cronos Group Inc. 
                if cols[0].text is None:
                        continue
                elif "Garibaldi Resources" in cols[0].text.strip():
                        name = cols[0].text.strip()
                        while True:
                                # check for invalid row ie we gotr all the news
                                temp = rows[counter + 1]("td")
                                if len(temp) is 1:
                                        break #finished
                                
                                date = temp[1].text.strip()
                                time = temp[2].text.strip()
                                headline = temp[3].text.strip() #News Release - English
                                #www.sedar.com/GetFile.do?lang=EN + link
                                link = 'http://www.sedar.com/GetFile.do?lang=EN' + temp[3].a.get('title')
                                
                                news = news_item(headline, link, date, time)
                                if news not in news_list:
                                    news_list.append(news)
                                    print("Found new {} SEDAR release!!".format(name))
                                    output = 'New Sedar Filing for {}: {} {} - {}({})'.format(name, date, time, headline, link)
                                    await client.send_message(channel, '{} - {} ({})'.format(date, headline, link))
                                else:
                                    print("skipping old news item")

                                counter += 1
                        break                     
                counter += 1
        print("No GGI updates found, sleeping.")
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