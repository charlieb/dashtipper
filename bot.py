import os
import asyncio
import discord
from discord.ext import commands
from aiomysql import connect
from pifkoin.bitcoind import Bitcoind, BitcoindException
import qrcode

import mysql.connector as mysql
import random

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''
bot = commands.Bot(command_prefix='?', description=description)

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

def is_registered(user):
    '''Returns a boolean for whether the user is found in the database'''

    conn = mysql.connect(host='127.0.0.1', port=3306,
                               user='root', password='password',
                               db='tipper')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = %s;', (user,))
    registered = len(cur.fetchall()) > 0
    cur.close()
    conn.close()

    return registered

def new_user(id, name):
    '''Adds a user to the database'''

    conn = mysql.connect(host='127.0.0.1', port=3306,
                               user='root', password='password',
                               db='tipper')
    cur = conn.cursor()
    cur.execute('INSERT INTO users (name, id) VALUES (%s, %s);', (name, id))
    conn.commit()
    cur.close()
    conn.close()

def new_tx(from_id, to_id, amount):
    '''Adds a new transaction (tip) to the database'''

    conn = mysql.connect(host='127.0.0.1', port=3306,
                               user='root', password='password',
                               db='tipper')
    cur = conn.cursor()
    cur.execute('INSERT INTO transactions (from_id, to_id, state, amount) VALUES (%s, %s, \'new\', %s);', (from_id, to_id, amount))
    conn.commit()
    cur.close()
    conn.close()

####################################################################33

@bot.command(pass_context=True)
@asyncio.coroutine
def newaddress(ctx):
    '''Resends the user's current account address'''

    # Author is a Member
    id = ctx.message.author.id

    if not is_registered(id):
        yield from bot.say('You are not registered. Use ?register to create an account.')
        return

    dconn = Bitcoind('~/.dashcore/dash.conf', rpcport=19998) # testnet, 9998 is realnet
    addr = dconn.getnewaddress(id)

    # Generate and save a QR code with the address
    im = qrcode.make(addr)
    filename = '/tmp/' + addr + '.png'
    im.save(filename, 'png')

    yield from bot.say('Your tip wallet address is %s.'%(addr))
    yield from bot.send_file(ctx.message.channel, filename)

    # Clean up the image file
    os.remove(filename)

@bot.command(pass_context=True)
@asyncio.coroutine
def getaddress(ctx):
    '''Resends the user's current account address'''

    # Author is a Member
    id = ctx.message.author.id

    if not is_registered(id):
        yield from bot.say('You are not registered. Use ?register to create an account.')
        return

    dconn = Bitcoind('~/.dashcore/dash.conf', rpcport=19998) # testnet, 9998 is realnet
    addr = dconn.getaccountaddress(id)
    dconn.setaccount(addr, id)

    # Generate and save a QR code with the address
    im = qrcode.make(addr)
    filename = '/tmp/' + addr + '.png'
    im.save(filename, 'png')

    yield from bot.say('Your tip wallet address is %s.'%(addr))
    yield from bot.send_file(ctx.message.channel, filename)

    # Clean up the image file
    os.remove(filename)

@bot.command(pass_context=True)
@asyncio.coroutine
def register(ctx):
    '''Adds a user to the database, generates a wallet for them, gives them its address to send funds to.'''

    # Author is a Member
    id = ctx.message.author.id
    name = ctx.message.author.name

    if is_registered(id):
        yield from bot.say('You are already registered. Use ?getaddress to get your tip wallet address')
        return
    
    new_user(id, name)

    # Generate a new address
    dconn = Bitcoind('~/.dashcore/dash.conf', rpcport=19998) # testnet, 9998 is realnet
    addr = dconn.getnewaddress()
    dconn.setaccount(addr, id)

    # Generate and save a QR code with the address
    im = qrcode.make(addr)
    filename = '/tmp/' + addr + '.png'
    im.save(filename, 'png')

    yield from bot.say('Welcome %s, your tip wallet address is %s.\nPlease send some dash here to be able to tip.'%(name, addr))
    yield from bot.send_file(ctx.message.channel, filename)

    # Clean up the image file
    os.remove(filename)

@bot.command(pass_context=True)
@asyncio.coroutine
def send(ctx, addr, amount):
    '''Send from my account to abitrary dash address'''

    # Author is a Member
    id = ctx.message.author.id

    if not is_registered(id):
        yield from bot.say('You are not registered. Use ?register to create an account.')
        return
    
    dconn = Bitcoind('~/.dashcore/dash.conf', rpcport=19998) # testnet, 9998 is realnet
    balance = dconn.getbalance(id)
    if float(amount) > balance:
        yield from bot.say('You can only send up to %f.'%balance)
        return

    txid = dconn.sendfrom(id, addr, amount)

    # Generate and save a QR code with the address
    im = qrcode.make(txid)
    filename = '/tmp/' + txid + '.png'
    im.save(filename, 'png')

    yield from bot.say('Your transaction id is %s.'%(txid))
    yield from bot.send_file(ctx.message.channel, filename)

    # Clean up the image file
    os.remove(filename)

@bot.command(pass_context=True)
@asyncio.coroutine
def tip(ctx, to_user, amount):
    '''Send a tip to another user'''

    # Author is a Member
    from_id = ctx.message.author.id

    if not is_registered(from_id):
        yield from bot.say('You are not registered. Use ?register to create an account.')
        return

    dconn = Bitcoind('~/.dashcore/dash.conf', rpcport=19998) # testnet, 9998 is realnet
    balance = dconn.getbalance(from_id)
    if float(amount) > balance:
        yield from bot.say('You can only send up to %f.'%balance)
        return

    if to_user.startswith('<@') and to_user.endswith('>'):
        to_id = to_user[2:-1]
    else:
        yield from bot.say('Bad user id "%s", please use @ symbol so Discord sends me a user id.'%to_user)
        return

    new_tx(from_id, to_id, float(amount))
    yield from bot.say('A tip of %s dash will be offered to %s.'%(amount, to_user))


    
rates = {}
@asyncio.coroutine
def update_prices():
    '''Updates trading pair rates'''
    global rates
    while True:
        rates['DASH/USD'] = random.random() * 500
        rates['DASH/BTC'] = random.random() 
        yield from asyncio.sleep(5)

@bot.command()
@asyncio.coroutine
def prices():
    global rates
    yield from bot.say('\n'.join('%s: %f'%(pair, price) for pair, price in rates.items()))


bot.loop.create_task(update_prices())
bot.run('MzgwODI4NjkzMzA1NDkxNDY5.DPDNHA.zyO0ox0QBacQqEIuTD7Ch9q88NE')
