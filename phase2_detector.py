from telethon import TelegramClient, events
import asyncio
from datetime import datetime
import pytz

API_ID = 14424659
API_HASH = "5facb0b7b7a6f141da79d9cc460d4e12"

# Source channel
SOURCE_CHANNEL = -1003170522699

# Your private "Guns' Goldbot" output channel
OUTPUT_CHANNEL = -1002933896146

ZIMBABWE_TZ = pytz.timezone("Africa/Harare")


async def main():

    client = TelegramClient(
        "gold_signal_bot",
        API_ID,
        API_HASH
    )

    print("========================================")
    print("PHASE 2 - TELEGRAM SIGNAL DETECTOR")
    print("========================================")
    print()

    print("Connecting to Telegram...")

    await client.connect()

    if not await client.is_user_authorized():
        print("❌ SESSION NOT AUTHORIZED")
        await client.disconnect()
        return

    print("✅ SESSION AUTHORIZED")
    print()

    # Verify source channel
    try:
        source = await client.get_entity(SOURCE_CHANNEL)

        print("SOURCE CHANNEL:")
        print(f"   Name: {source.title}")
        print(f"   ID: {source.id}")
        print("   Status: ✅ ACCESSIBLE")

    except Exception as e:
        print("❌ Could not access source channel")
        print(f"Error: {e}")
        await client.disconnect()
        return

    print()

    # Verify output channel
    try:
        output = await client.get_entity(OUTPUT_CHANNEL)

        print("OUTPUT CHANNEL:")
        print(f"   Name: {output.title}")
        print(f"   ID: {output.id}")
        print("   Status: ✅ ACCESSIBLE")

    except Exception as e:
        print("❌ Could not access output channel")
        print(f"Error: {e}")
        await client.disconnect()
        return

    print()
    print("========================================")
    print("LISTENER IS ACTIVE")
    print("========================================")
    print()
    print("Waiting for NEW messages from:")
    print("GUNS THE TRADER")
    print()
    print("Press CTRL+C to stop.")
    print()

    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):

        try:

            message_text = event.message.text or ""

            now = datetime.now(ZIMBABWE_TZ)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            print()
            print("📨 NEW MESSAGE DETECTED")
            print("----------------------------------------")
            print(f"Time: {timestamp}")
            print(f"Channel: {event.chat.title}")
            print(f"Message ID: {event.message.id}")
            print()
            print(message_text)
            print("----------------------------------------")

            # Send simple detection notification.
            notification = (
                "📨 <b>NEW SIGNAL MESSAGE DETECTED</b>\n"
                "────────────────\n"
                f"📺 <b>Channel:</b> {event.chat.title}\n"
                f"🆔 <b>Message ID:</b> {event.message.id}\n"
                f"⏰ <b>Time:</b> {timestamp}\n\n"
                f"<b>Message:</b>\n{message_text}"
            )

            await client.send_message(
                OUTPUT_CHANNEL,
                notification,
                parse_mode="html"
            )

            print("✅ Detection notification sent to Guns' Goldbot")

        except Exception as e:

            print()
            print("❌ Error processing message:")
            print(e)


    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())