import asyncio
import time
from typing import List, Optional, Tuple

from telegram import Bot

from environment import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_POLL_TIMEOUT

BOT = Bot(token=TELEGRAM_BOT_TOKEN)


def send_messages_and_wait_for_approval(messages: List[str]) -> Tuple[bool, Optional[str]]:
    """Send a message to the Telegram bot and wait for an approval or disapproval response."""
    for msg in messages:
        asyncio.run(send_bot_message_async(msg))
    response = wait_for_latest_message_to_be_approve_or_disapprove()
    if "approve" in response.lower():
        send_message("Action approved. Proceeding with the operation.")
        return True, None
    elif "disapprove" in response.lower():
        send_message("Action disapproved. Aborting the operation.")
        return False, None

    send_message("Action modification requested. Retrying with modified instructions.")
    return False, response


def send_message(text: str) -> None:
    """Send a message to the Telegram bot."""
    asyncio.run(send_bot_message_async(text))


def wait_for_latest_message_to_be_approve_or_disapprove() -> str:
    print(
        f"Waiting for up to {TELEGRAM_POLL_TIMEOUT} seconds for approval or disapproval message..."
    )
    send_message("Please respond with /approve, /disapprove, or /modify to indicate your decision.")
    start = time.time()

    while time.time() - start < TELEGRAM_POLL_TIMEOUT:

        messages = asyncio.run(read_bot_messages_async(after_time=start))
        for message in messages:
            if "disapprove" in message.lower():
                print("Received disapproval message.")
                return "disapprove"
            elif "approve" in message.lower():
                print("Received approval message.")
                return "approve"
            elif "modify" in message.lower():
                print("Received modify message. Treating as disapproval for now.")
                return message

        time.sleep(0.5)  # Sleep briefly to avoid busy waiting
    print("No approval or disapproval message received; defaulting to disapprove")
    return "disapprove"


async def read_bot_messages_async(after_time: float) -> List[str]:

    message_stack = []

    async with BOT:
        # Get updates
        updates = await BOT.get_updates(timeout=TELEGRAM_POLL_TIMEOUT)

        if not updates:
            print(f"No messages found after up to {TELEGRAM_POLL_TIMEOUT} seconds.")
            return []
        else:
            for update in updates:
                if update.message:
                    message_text = update.message.text
                    message_time = update.message.date
                    message_timestamp = message_time.timestamp()
                    if message_timestamp >= after_time:
                        message_stack.append(message_text)
            print(
                f"Found {len(message_stack)} messages after up to {TELEGRAM_POLL_TIMEOUT} seconds."
            )

    return message_stack


async def send_bot_message_async(text: str) -> None:
    async with BOT:
        await BOT.send_message(text=text, chat_id=TELEGRAM_CHAT_ID)


if __name__ == "__main__":
    # Example usage
    print("Sending message and waiting for approval...")
    approved = send_messages_and_wait_for_approval(
        "Hello from Python! Live long and prosper. Please approve or disapprove this action."
    )
    print(f"Approved: {approved}")
