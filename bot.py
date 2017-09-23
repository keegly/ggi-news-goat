import asyncio
import random
from timeit import default_timer as timer
import discord
from bs4 import BeautifulSoup
import aiohttp

description = """a GGI news feed bot"""

client = discord.Client()
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
        return self.text == other.text

    date = ""
    text = ""
    link = ""


async def get_news():
    await client.wait_until_ready()
    #channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        # http://www.newswire.ca/news-releases/all-public-company-news/?month=8&day=01&year=2017&hour=14
        url = 'http://www.newswire.ca/news-releases/all-public-company-news/'
        sleep_time = random.randint(25, 35)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        sleep_time *= 2
                        print("HTTP Request for {} failed with status {}, sleeping for {}.".format(
                            url, r.status, sleep_time))
                    elif r.status == 200:
                        print("HTTP Request for {} successful with status {}".format(
                            url, r.status))
                        start = timer()
                        soup = BeautifulSoup(await r.text(), 'lxml')
                        # res = soup.find_all('a', {"class" : "news-release"})
                        # only grab the NR's
                        res = soup.find_all('div', {"class": "row"})[5:25]
                        for item in res:
                            headline = item.contents[3].text.strip()
                            headline = headline.split("\n")[0]
                            link = item.contents[3].a.get("href")
                            date = item.contents[1].text.strip()
                            time = ""
                            if "Garibaldi" in headline:  # found new NR
                                news = news_item(headline, link, date, time)
                                if news not in news_list:
                                    news_list.append(news)
                                    print("Found new GGI release!!")
                                    output = '{} > {} ({})'.format(
                                        date, headline, link)
                                    await client.send_message(channel, output)
                                else:
                                    print("Skipping old news item")
                            elif "GGI" in headline:  # halt/resumption notice
                                halt = halt_item(headline, link, date)
                                if halt not in halt_list:
                                    halt_list.append(halt)
                                    print("Found new GGI halt/resumption notice!!")
                                    output = '{} > {} ({})'.format(
                                        date, headline, link)
                                    await client.send_message(channel, output)
                                else:
                                    print("Skipping old halt/resumption item")
                        end = timer()
                        print("GGI update search complete in {:.2f}s, sleeping for {}s.".format(
                            (end - start), sleep_time))
        except (aiohttp.ClientResponseError,
                aiohttp.ClientOSError,
                asyncio.TimeoutError) as exc:
            try:
                code = exc.code
            except AttributeError:
                code = ''
            print("aiohttp exception: {}".format(code))
        except Exception:
            print("Unknown error occureed")

        await asyncio.sleep(sleep_time)


async def get_halted():
    await client.wait_until_ready()
    #channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action

    while not client.is_closed:
        url = 'http://iiroc.mediaroom.com'
        sleep_time = random.randint(25, 35)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        sleep_time *= 2
                        print("HTTP Request for {} failed with status {}, sleeping for {}.".format(
                            url, r.status, sleep_time))
                    elif r.status == 200:
                        start = timer()
                        print("HTTP Request for {} successful with status {}".format(
                            url, r.status))
                        soup = BeautifulSoup(await r.text(), 'lxml')
                        res = soup.find_all('div', {"class": "item"})
                        for item in res:
                            date = item.contents[1].string.strip()
                            text = item.contents[2].string.strip()
                            link = item.contents[2].a.get("href")

                            if 'GGI' in text:
                                halt = halt_item(text, link, date)
                                if halt not in halt_list:
                                    halt_list.append(halt)
                                    print("Found new GGI Halt/Resumption notice")
                                    output = '{} > {} ({})'.format(
                                        date, text, link)
                                    await client.send_message(channel, output)
                                else:
                                    print("Skipping old halt/resumption item")
                        end = timer()
                        print("Halt search complete in {:.2f}s, sleeping for {}s".format(
                            (end - start), sleep_time))
        except (aiohttp.ClientResponseError,
                aiohttp.ClientOSError,
                asyncio.TimeoutError) as exc:
            try:
                code = exc.code
            except AttributeError:
                code = ''
            print("aiohttp exception: {}".format(code))
        except Exception:
            print("Unknown error occurred")

        await asyncio.sleep(sleep_time)


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
        print("Command .news received from {} ({})".format(
            message.author, message.author.nick))
        output = ""
        if len(news_list) is 0:
            output = "Wait a sec, what's this? Found some new GGI News!"
            await client.send_message(message.channel, output)
            await asyncio.sleep(5)
            output = "Got your goat! Just kidding, still no news."
            await client.send_message(message.channel, output)
            return
            # output = "No recent news for GGI."
        for nr in news_list[:5]:
            # post the most recent 5 items
            output += '{} - {} ({})\n'.format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.latest'):
        output = ""
        print("Command .latest received from {} ({})".format(
            message.author, message.author.nick))
        if len(news_list) is 0:
            output = "No recent news for GGI"
        else:
            nr = news_list[0]
            output = "{} - {}({})".format(nr.date, nr.headline, nr.link)
            print("Printing most recent news release for {} ({})".format(
                message.author.nick, message.author))
        await client.send_message(message.channel, output)

    elif message.content.startswith('.halt'):
        output = ""
        print("Command .halt received from {} ({})".format(
            message.author, message.author.nick))
        if len(halt_list) is 0:
            output = "No recent IIROC Trading Halts for GGI"
        else:
            halt = halt_list[-1]
            # post the most recent item
            output = '{} > {} ({})'.format(halt.date, halt.text, halt.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.clap'):
        if message.author.id == '357169509338972161':  # ignore own comments
            return

        print("Command .clap received from {} ({})".format(
            message.author, message.author.nick))
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
