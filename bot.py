import asyncio
import os
import urllib.parse
import psycopg2
import logging
from random import randint
from timeit import default_timer as timer
import discord
from bs4 import BeautifulSoup
import aiohttp

description = """a GGI news feed bot"""

client = discord.Client()
token = "MzU3MTY5NTA5MzM4OTcyMTYx.DJl_ig.IBYtxryOuYyVHfl2ahXgfj6Nwt0"

news_list = [] # pylint: disable=C0103
halt_list = [] # pylint: disable=C0103

class NewsItem():
    def __init__(self, headline, link, date):
        self.headline = headline
        self.link = link
        self.date = date

    def __eq__(self, other):
        return self.headline == other.headline

    headline = ""
    date = ""
    time = ""
    link = ""


class HaltItem():
    def __init__(self, text, link, date):
        self.date = date
        self.text = text
        self.link = link

    def __eq__(self, other):
        return self.text == other.text

    date = ""
    text = ""
    link = ""

async def scrape(url):
    """ Scrape a given URL and return a beautiful soup object ready for use """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    logging.error("HTTP Request for %.22s failed with status %d.", url, r.status)
                    soup = None
                elif r.status == 200:
                    logging.info("HTTP Request for %.22s... successful with status %d",
                                 url, r.status)
                    soup = BeautifulSoup(await r.text(), 'lxml')
                return soup
    except (aiohttp.ClientResponseError,
            aiohttp.ClientOSError,
            asyncio.TimeoutError) as exc:
        try:
            code = exc.code
        except AttributeError:
            code = ''
        logging.exception("aiohttp exception: %s", code)
    except Exception as exc:
        logging.exception("Unknown error occurred: %s", exc)


async def get_news():
    """ Parse newswire and see if they've any GGI releases for us """
    await client.wait_until_ready()
    # channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        # http://www.newswire.ca/news-releases/all-public-company-news/?month=8&day=01&year=2017&hour=14
        url = 'http://www.newswire.ca/news-releases/all-public-company-news/' # ?c=n?page=1&pagesize=200
        sleep_time = randint(10, 25)
        soup = await scrape(url)
        if soup is None: # HTTP req failed, so wait longer before trying again
            sleep_time *= 2
            logging.info("Sleeping for %ds", sleep_time)
        else:
            start = timer()
            res = soup.find_all('div', {"class": "row"})[5:25]
            for item in res:
                try:
                    headline = item.contents[3].text.strip()
                    headline = headline.split("\n")[0]
                    link = item.contents[3].a.get("href")
                    date = item.contents[1].text.strip()
                except (AttributeError, IndexError) as exc:
                    logging.exception("Error Parsing HTML: %s", exc)
                    continue

                if "Garibaldi" in headline:  # found new NR
                    news = NewsItem(headline, link, date)
                    if news not in news_list:
                        news_list.append(news)
                        logging.info("Found new GGI release!!")
                        output = '{} > {} ({})'.format(
                            date, headline, link)
                        await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old news item")
                elif "GGI" in headline:  # halt/resumption notice
                    halt = HaltItem(headline, link, date)
                    if halt not in halt_list:
                        halt_list.append(halt)
                        logging.info("Found new GGI halt/resumption notice!!")
                        output = '{} > {} ({})'.format(
                            date, headline, link)
                        await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old halt/resumption item")
            end = timer()
            logging.info("GGI update search complete in {:.2f}s, sleeping for {}s."
                         .format((end - start), sleep_time))

        await asyncio.sleep(sleep_time)


async def get_halted():
    """ Parse IIROC and see if we got any halt/resumption notices """
    await client.wait_until_ready()
    # channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action

    while not client.is_closed:
        url = 'http://iiroc.mediaroom.com'
        sleep_time = randint(10, 25)
        soup = await scrape(url)
        if soup is None:    # failed HTTP req
            sleep_time *= 2
            logging.info("Sleeping for %ds", sleep_time)
        else:
            start = timer()
            res = soup.find_all('div', {"class": "item"})
            for item in res:
                try:
                    date = item.contents[1].string.strip()
                    text = item.contents[2].string.strip()
                    link = item.contents[2].a.get("href")
                except (AttributeError, IndexError) as exc:
                    logging.exception("Error Parsing HTML: %s", exc)
                    continue

                if 'GGI' in text:
                    halt = HaltItem(text, link, date)
                    if halt not in halt_list:
                        halt_list.append(halt)
                        logging.info("Found new GGI Halt/Resumption notice")
                        output = '{} > {} ({})'.format(
                            date, text, link)
                        await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old halt/resumption item")
            end = timer()
            logging.info("Halt search complete in {:.2f}s, sleeping for {}s".format(
                (end - start), sleep_time))

        await asyncio.sleep(sleep_time)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('-------')
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    # TODO: Do an inital scrape here to populate any existing news without outputting it to chat
    #       Because this is just poverty
    headline = 'Garibaldi Financing Revised'
    link = 'http://www.newswire.ca/news-releases/garibaldi-financing-revised-648074313.html'
    date = 'Sep 26, 2017, 19:33 ET'
    news = NewsItem(headline, link, date)
    news_list.append(news)
    await client.change_presence(game=discord.Game(name='Shit Just Goat Real'))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('.news'):
        logging.info("Command .news received from %s (%s)", message.author, message.author.nick)
        output = ""
        if len(news_list) is 0:
            num = randint(0, 10)
            if num < 7:
                output = "Wait a sec, what's this? Found some new GGI News!"
                tmp = await client.send_message(message.channel, output)
                await asyncio.sleep(4)
                output = "Got your goat! Just kidding, still no news."
                await client.edit_message(tmp, output)
                return
            else:
                output = "No news for GGI."
        for nr in news_list[-5:]:
            # post the most recent 5 items
            output += '{} - {} ({})\n'.format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.latest'):
        output = ""
        logging.info("Command .latest received from %s (%s)", message.author, message.author.nick)
        if len(news_list) is 0:
            output = "❌ No news for GGI ❌"
        else:
            nr = news_list[0]
            output = "{} - {}({})".format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.halt'):
        output = ""
        logging.info("Command .halt received from %s (%s)", message.author, message.author.nick)
        if len(halt_list) is 0:
            output = "❌ GGI.V: Not Halted ❌"
        else:
            halt = halt_list[-1]
            # post the most recent item
            output = '{} > {} ({})'.format(halt.date, halt.text, halt.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.clap'):
        logging.info("Command .clap received from %s (%s)", message.author, message.author.nick)
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

# TODO: preload news list from DB here?
client.loop.create_task(get_news())
client.loop.create_task(get_halted())
client.run(token)
