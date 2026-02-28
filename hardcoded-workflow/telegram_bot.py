import asyncio
from typing import List

from telegram import Bot

from constants import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_POLL_TIMEOUT

bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def read_messages() -> List[str]:

    message_stack = []

    # Get updates
    updates = await bot.get_updates(timeout=TELEGRAM_POLL_TIMEOUT)

    if not updates:
        print(f"No messages found after {TELEGRAM_POLL_TIMEOUT} seconds.")
        return []
    else:
        for update in updates:
            if update.message:
                message_text = update.message.text
                message_stack.append(message_text)
        print(f"Found {len(message_stack)} messages after {TELEGRAM_POLL_TIMEOUT} seconds.")
    return message_stack


async def send_message(text: str, chat_id: str) -> None:
    async with bot:
        await bot.send_message(text=text, chat_id=chat_id)


if __name__ == "__main__":
    asyncio.run(send_message("Hello from Python! Live long and prosper.", TELEGRAM_CHAT_ID))
    messages = asyncio.run(read_messages())
    print("Messages received from Telegram:")
    print(messages)
