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

news_list = []       # pylint: disable=C0103
halt_list = []       # pylint: disable=C0103
stockwatch_list = [] # pylint: disable=C0103
# ggi-price-actioon and private serv
output_channels = [discord.Object(id='365150978439381004'), # pylint: disable=C0103
                   discord.Object(id='354637284147986433')] # pylint: disable=C0103
#output_channels = [discord.Object(id='355892436888715279')] # testing

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
                    logging.debug(r.headers)
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
                if news not in stockwatch_list:
                    stockwatch_list.append(news)
                    for channel in output_channels:
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
                        for channel in output_channels:
                            await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old news item (%s)", headline)
                elif "GGI" in headline:  # halt/resumption notice
                    halt = HaltItem(headline, link, date)
                    if halt not in halt_list:
                        halt_list.append(halt)
                        logging.info("Found new GGI halt/resumption notice!!")
                        output = "{} > {} > {}".format(
                            date, headline, link)
                        for channel in output_channels:
                            await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old halt/resumption item (%s)", headline)
            end = timer()
            logging.info("Newswire update search complete in {:.2f}s, sleeping for {}s."
                         .format((end - start), sleep_time))

        await asyncio.sleep(sleep_time)

async def get_company_news():
    """ Check directly off of the Garibaldi site as well """
    await client.wait_until_ready()
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
                    for channel in output_channels:
                        await client.send_message(channel, output)
                else:
                    logging.info("Skipping old news item (%s)", headline)

            end = timer()
            logging.info("Company site update search complete in {:.2f}s, sleeping for {}s."
                         .format((end - start), sleep_time))

        await asyncio.sleep(sleep_time)

async def get_halted():
    """ Parse IIROC and see if we got any halt/resumption notices """
    await client.wait_until_ready()

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
                        output = "{} > {} > {}".format(date, text, link)
                        for channel in output_channels:
                            await client.send_message(channel, output)
                    else:
                        logging.info("Skipping old halt/resumption item (%s)", text)
            end = timer()
            logging.info("Halt search complete in {:.2f}s, sleeping for {}s".format(
                (end - start), sleep_time))

        await asyncio.sleep(sleep_time)

async def get_email():
    await client.wait_until_ready()
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
    await client.change_presence(game=discord.Game(name='Organic, Free Range, FLOW GOAT™ Approved'))

@client.event
async def on_message(message): 
    if message.author == client.user:
        return

    # connor or bebster
#    if message.author.id in ['354793851040563202']:
#        await client.add_reaction(message, u"\U0001F415")
#        return

    if 'newsgoat' in (word.lower() for word in message.content.split()):
        await client.send_message(message.channel, u"\U0001F410")
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

    elif message.content.startswith('.stockwatch'):
        output = ""
        logging.info("Command .stockwatch received from %s (%s)", message.author, message.author.nick)
        if len(stockwatch_list) is 0:
            output = "❌ No news for GGI ❌"
        else:
            nr = stockwatch_list[-1]
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
        output = u"\U0001F410"
        tmp = await client.send_message(message.channel, output)
        for word in words:
            output += word
            output += u"\U0001F410"
            await client.edit_message(tmp, output)
            asyncio.sleep(0.5)

def init():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    preload_news_items()
    preload_stockwatch_items()
    preload_halt_items()

# TODO: preload news list from DB here?

def preload_news_items():
    """ TODO: Do an inital scrape here to populate any existing news without outputting it to chat
              Because this is just poverty """
    logging.info("Preloading Company Site Items.")
    url = 'http://www.garibaldiresources.com/s/NewsReleases.asp'
    soup = client.loop.run_until_complete(scrape(url))
    if soup is None: # HTTP req failed, so wait longer before trying again
        logging.info("Prefetching GGI/Newswire items failed.")
    else:
        start = timer()
        table = soup.find_all('tr')[:5] # grab only the most recent 3
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
        end = timer()
        logging.info("Company site preload complete in {:.2f}s".format(
            (end - start)))
        news_list.reverse()

def preload_stockwatch_items():
    logging.info("Preloading Stockwatch Items.")
    url = 'https://www.stockwatch.com/Quote/Detail.aspx?symbol=GGI&region=C'
    soup = client.loop.run_until_complete(scrape(url))
    if soup is None: # HTTP req failed, so wait longer before trying again
        logging.info("Prefetching Stockwatch items failed.")
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
            if news not in stockwatch_list:
                stockwatch_list.append(news)

        stockwatch_list.reverse()
        end = timer()
        logging.info("Stockwatch preload complete in {:.2f}s".format(
        (end - start)))

def preload_halt_items():
    logging.info("Preloading IIROC Halt Items.")
    url = 'http://iiroc.mediaroom.com'
    soup = client.loop.run_until_complete(scrape(url))
    if soup is None:    # failed HTTP req
        logging.info("Prefetching IIROC Halt items failed.")
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
        end = timer()
        logging.info("Halt search complete in {:.2f}s".format(
            (end - start)))

init()

client.loop.create_task(get_stockwatch())
client.loop.create_task(get_company_news())
client.loop.create_task(get_news())
client.loop.create_task(get_halted())
# client.loop.create_task(get_email())
client.run(token)
