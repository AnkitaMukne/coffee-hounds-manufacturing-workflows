import asyncio
from telegram import Bot

TELEGRAM_BOT_TOKEN = '8391945774:AAGCryNT_t-ePLJcFI2lrNZTqVm8gBH9RQk'
CHAT_ID = '-1003833527945'

async def main():

    #Create bot object
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    #Get updates
    updates = await bot.get_updates()

    if not updates:
        print("No updates found")
    else:
        for update in updates:
            if update.message:

                #Show all message data if needed
                #print(update.message)

                #Show only chat id, title and message
                #chat_id = update.message.chat.id
                #chat_title = update.message.chat.title
                message_text = update.message.text
                
        print(f"Message: {message_text}")
asyncio.run(main())

'''bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_message(text, chat_id):
    async with bot:
        await bot.send_message(text=text, chat_id=chat_id)

async def run_bot(messages, chat_id):
    text = '\n'.join(messages)
    await send_message(text, chat_id)

#Test messages
messages = [
    'Hello from Python! Live long and prosper.',
]

if messages:
    asyncio.run(run_bot(messages, CHAT_ID))'''