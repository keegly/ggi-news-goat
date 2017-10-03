import asyncio
import logging
import ssl
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
        async with aiohttp.ClientSession(headers={'Cache-Control':'no-cache'}) as session:
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

async def get_stockwatch():
    """ Check stockwatch since apparently it's the fucking fastest... """
    await client.wait_until_ready()
    # channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        url = 'https://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C'
        sleep_time = randint(10, 25)
        soup = await scrape(url)
        if soup is None: # HTTP req failed, so wait longer before trying again
            sleep_time *= 2
            logging.info("Sleeping for %ds", sleep_time)
        else:
            start = timer()
            table = soup.find(id="MainContent_NewsList1_Table1_Table1")
            rows = table("tr")[1:] # skip header, grab first 3
            for tr in rows:
                cols = tr("td")  # Equiv to .findAll("td")
        
                headline = cols[5].string.strip()
                link = 'http://www.stockwatch.com' + cols[5].a.get('href')
                date = cols[0].string.strip()

                news = NewsItem(headline, link, date)
                if news not in news_list:
                    news_list.append(news)
                    await client.send_message(channel, '{} > {} > {}'.format(date, headline, link))
                else:
                    logging.info("Skipping old news item (%s)", headline)

            end = timer()
            logging.info("Stockwatch search complete in {:.2f}s, sleeping for {}s."
                         .format((end - start), sleep_time))
        await asyncio.sleep(sleep_time)

async def get_news():
    """ Parse newswire and see if they've any GGI releases for us """
    await client.wait_until_ready()
    # channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
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
                        output = "{} > {} > {}".format(
                            date, headline, link)
                        await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old news item")
                elif "GGI" in headline:  # halt/resumption notice
                    halt = HaltItem(headline, link, date)
                    if halt not in halt_list:
                        halt_list.append(halt)
                        logging.info("Found new GGI halt/resumption notice!!")
                        output = "{} > {} > {}".format(
                            date, headline, link)
                        await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old halt/resumption item")
            end = timer()
            logging.info("Newswire update search complete in {:.2f}s, sleeping for {}s."
                         .format((end - start), sleep_time))

        await asyncio.sleep(sleep_time)

async def get_company_news():
    """ Check directly off of the Garibaldi site as well """
    await client.wait_until_ready()
    # channel = discord.Object(id='355892436888715279') # test server
    channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        url = 'http://www.garibaldiresources.com/s/NewsReleases.asp'
        sleep_time = randint(20, 30)
        soup = await scrape(url)
        if soup is None: # HTTP req failed, so wait longer before trying again
            sleep_time *= 2
            logging.info("Sleeping for %ds", sleep_time)
        else:
            start = timer()
            table = soup.find_all('tr')[:3] # grab only the most recent 3
            for tr in table:
                cols = tr("td")  # Equiv to .findAll("td")
                try:
                    date = cols[0].text.strip()
                    headline = cols[1].string.strip()
                    link = 'http://www.garibaldiresources.com' + cols[0].a.get("href")
                except (AttributeError, IndexError) as exc:
                    logging.exception("Error Parsing HTML: %s", exc)
                    continue
                news = NewsItem(headline, link, date)
                if news not in news_list:
                    news_list.append(news)
                    logging.info("Found new GGI release!!")
                    output = "{} > {} > {}".format(date, headline, link)
                    await client.send_message(channel, output)
                else:
                    logging.info("Skipping old news item")

            end = timer()
            logging.info("Company site update search complete in {:.2f}s, sleeping for {}s."
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
                        output = "{} > {} > {}".format(
                            date, text, link)
                        await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old halt/resumption item")
            end = timer()
            logging.info("Halt search complete in {:.2f}s, sleeping for {}s".format(
                (end - start), sleep_time))

        await asyncio.sleep(sleep_time)

async def get_email():
    await client.wait_until_ready()

    channel = discord.Object(id='355892436888715279') # test server
    # channel = discord.Object(id='354637284147986433')  # ggi-price-action
    while not client.is_closed:
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sleep_time = randint(10, 25)   

        await asyncio.sleep(sleep_time)


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('-------')
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    await client.change_presence(game=discord.Game(name='Shit Just Goat Real'))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.author.id not in ['236291672655396864', '354632104090271746', '354636345479528448']:
        return

    if message.content.startswith('.recent'):
        logging.info("Command .recent received from %s (%s)", message.author, message.author.nick)
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
            output += '{} > {} > {}\n'.format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.news'):
        output = ""
        logging.info("Command .news received from %s (%s)", message.author, message.author.nick)
        if len(news_list) is 0:
            output = "❌ No news for GGI ❌"
        else:
            nr = news_list[-1]
            output = "{} > {} > {}".format(nr.date, nr.headline, nr.link)
        await client.send_message(message.channel, output)

    elif message.content.startswith('.halt'):
        output = ""
        logging.info("Command .halt received from %s (%s)", message.author, message.author.nick)
        if len(halt_list) is 0:
            output = "❌ GGI.V: Not Halted ❌"
        else:
            halt = halt_list[-1]
            # post the most recent item
            output = "{} > {} > {}".format(halt.date, halt.text, halt.link)
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

    elif message.content.startswith('.goat'):
        logging.info("Command .goat received from %s (%s)", message.author, message.author.nick)
        output = message.content
        output = output.replace(".goat", "")
        words = output.split()
        output = "🐐"
        tmp = await client.send_message(message.channel, output)
        for word in words:
            output += word
            output += "🐐"
            await client.edit_message(tmp, output)
            asyncio.sleep(0.5)

# TODO: preload news list from DB here? 🐐

def preload_news_items():
    """ TODO: Do an inital scrape here to populate any existing news without outputting it to chat
              Because this is just poverty """
    news_list.append(NewsItem('Garibaldi Commences Drilling At Nickel Mountain',
                              'http://www.garibaldiresources.com/s/NewsReleases.asp?ReportID=800969&_Type=News-Releases&_Title=Garibaldi-Commences-Drilling-At-Nickel-Mountain',
                              'August 24, 2017'))
    news_list.append(NewsItem('Garibaldi Intersects Broad Intervals Of Nickel-Copper Sulphide Mineralization In First Drill Hole At E&L',
                              'http://www.garibaldiresources.com/s/NewsReleases.asp?ReportID=801676&_Type=News-Releases&_Title=Garibaldi-Intersects-Broad-Intervals-Of-Nickel-Copper-Sulphide-Mineralizati...',
                              'September 01, 2017'))
    news_list.append(NewsItem('Garibaldi Financing Revised',
                              'http://www.garibaldiresources.com/s/NewsReleases.asp?ReportID=803825&_Type=News-Releases&_Title=Garibaldi-Financing-Revised',
                              'Sep 26, 2017, 19:33 ET'))

def preload_stockwatch_items():
    news_list.append(NewsItem('Garibaldi revises financing terms, grants options',
                              'https://www.stockwatch.com/News/Item.aspx?bid=Z-C%3aGGI-2509781&symbol=GGI&region=C',
                              '2017-09-26 19:24'))
    news_list.append(NewsItem('SEDAR MD & A',
                              'https://www.stockwatch.com/News/Item.aspx?bid=Z-C%3aGGI-2511512&symbol=GGI&region=C',
                              '2017-09-29 19:33'))
    news_list.append(NewsItem('SEDAR Interim Financial Statements',
                              'https://www.stockwatch.com/News/Item.aspx?bid=Z-C%3aGGI-2511511&symbol=GGI&region=C',
                              '2017-09-29 19:33'))
    news_list.append(NewsItem('Garibaldi closes $2.5M first tranche of placement',
                              'https://www.stockwatch.com/News/Item.aspx?bid=Z-C%3aGGI-2512115&symbol=GGI&region=C',
                              '2017-10-02 19:54'))
    news_list.append(NewsItem('SEDAR Early Warning Report',
                              'https://www.stockwatch.com/News/Item.aspx?bid=Z-C%3aGGI-2512374&symbol=GGI&region=C',
                              '2017-10-03 10:52'))
# preload_news_items()
preload_stockwatch_items()
client.loop.create_task(get_stockwatch())
# client.loop.create_task(get_company_news())
# client.loop.create_task(get_news())
client.loop.create_task(get_halted())
# client.loop.create_task(get_email())
client.run(token)
