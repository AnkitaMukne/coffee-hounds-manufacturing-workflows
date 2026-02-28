import asyncio

from telegram import Bot

from constants import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def read():

    message_stack = []

    # Get updates
    updates = await bot.get_updates()

    if not updates:
        print("No updates found")
    else:
        for update in updates:
            if update.message:

                # Show all message data if needed
                # print(update.message)

                # Show only chat id, title and message
                # chat_id = update.message.chat.id
                # chat_title = update.message.chat.title
                message_text = update.message.text
                message_stack.append(message_text)
        # print(f"Message: {message_text}")
    return message_stack


async def send_message(text, chat_id):
    async with bot:
        await bot.send_message(text=text, chat_id=chat_id)


async def run_bot(messages, chat_id):
    text = "\n".join(messages)
    await send_message(text, chat_id)


if __name__ == "__main__":
    messages = ["Hello from Python! Live long and prosper."]
    asyncio.run(run_bot(messages, TELEGRAM_CHAT_ID))  # To send messages to the Telegram channel
    asyncio.run(read())  # Reads messages from Telegram if any and returns them in a list
