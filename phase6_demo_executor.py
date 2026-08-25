import asyncio
import os
import re
import json
import hashlib
from datetime import datetime, timezone

import pytz
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError
from metaapi_cloud_sdk import MetaApi


# ============================================================
# PHASE 6 - DEMO TELEGRAM -> MT5 EXECUTOR
# ============================================================
# DEMO ONLY
# ============================================================

load_dotenv()

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

API_ID = int(os.getenv("TELEGRAM_API_ID", "14424659"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

STRING_SESSION = os.getenv("TELEGRAM_SESSION_STRING", "")
SESSION_NAME = "gold_signal_bot"

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN", "")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID", "")

SYMBOL = "XAUUSD_i"
LOT_SIZE = 0.01
POSITIONS_PER_SIGNAL = 2

ENTRY_EXTENSION_PIPS = 30
PRICE_EXTENSION = ENTRY_EXTENSION_PIPS / 10.0

TIMEZONE = pytz.timezone("Africa/Harare")

SOURCE_CHANNELS = [
    "Goldhunterlearnttade3867",
    "GoldSignalVip110",
    "MrHenrys122",
    "AGoldvip_0786",
    -1003170522699,
]

EXECUTED_FILE = "phase6_executed_signals.json"
TRADE_LOG_FILE = "phase6_trade_log.json"


# ------------------------------------------------------------
# TELEGRAM CLIENT
# ------------------------------------------------------------

if STRING_SESSION:
    client = TelegramClient(
        StringSession(STRING_SESSION),
        API_ID,
        API_HASH
    )
else:
    client = TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH
    )


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def normalize_text(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = text.replace("\u00A0", " ")
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def extract_direction(text):

    upper = text.upper()

    if re.search(r"\bBUY\b", upper):
        return "BUY"

    if re.search(r"\bSELL\b", upper):
        return "SELL"

    return None


def extract_entry(text):

    patterns = [

        r"\b(\d+(?:\.\d+)?)\s*[/_]\s*(\d+(?:\.\d+)?)\b",

        r"\b(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\b",

    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            a = float(match.group(1))
            b = float(match.group(2))

            return min(a, b), max(a, b)

    return None, None


def extract_sl(text):

    patterns = [

        r"\bSL\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)",

        r"\bSTOPLOSS\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)",

        r"\bSTOP\s+LOSS\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)",

    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return float(match.group(1))

    return None


def extract_tps(text):

    levels = {}

    matches = re.findall(
        r"\bTP\s*([1-9])\s*[:.\-=]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    for number, price in matches:

        levels[int(number)] = float(price)

    return dict(sorted(levels.items()))


def parse_signal(text):

    text = normalize_text(text)

    direction = extract_direction(text)
    entry_low, entry_high = extract_entry(text)
    sl = extract_sl(text)
    tps = extract_tps(text)

    errors = []

    if direction is None:
        errors.append("Missing BUY/SELL direction")

    if entry_low is None:
        errors.append("Missing entry")

    if sl is None:
        errors.append("Missing stop loss")

    if not tps:
        errors.append("No TP levels found")

    return {
        "direction": direction,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stoploss": sl,
        "tp_levels": tps,
        "parse_success": not errors,
        "validation_errors": errors,
    }


def choose_tp_mapping(channel, tps):

    if channel == "GUNS THE TRADER":

        if 6 in tps:
            return 3, 6

        return 3, 4

    if "GOLD SIGNAL VIP" in channel.upper():
        return 3, 6

    return 3, 4


def load_executed():

    if not os.path.exists(EXECUTED_FILE):
        return set()

    try:

        with open(EXECUTED_FILE, "r") as f:
            return set(json.load(f))

    except Exception:
        return set()


def save_executed(executed):

    with open(EXECUTED_FILE, "w") as f:
        json.dump(list(executed), f)


def append_trade_log(record):

    data = []

    if os.path.exists(TRADE_LOG_FILE):

        try:
            with open(TRADE_LOG_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = []

    data.append(record)

    with open(TRADE_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

async def main():

    print("=" * 70)
    print("PHASE 6 - DEMO TELEGRAM → MT5 EXECUTOR")
    print("=" * 70)

    print()
    print("⚠️ DEMO-ONLY MODE")
    print("⚠️ NO LIVE ACCOUNT TRADING ALLOWED")
    print()

    print(f"Symbol: {SYMBOL}")
    print(f"Lot per position: {LOT_SIZE}")
    print(f"Positions per signal: {POSITIONS_PER_SIGNAL}")
    print(f"Entry extension: {ENTRY_EXTENSION_PIPS} pips")
    print(f"Price extension: {PRICE_EXTENSION}")

    print()
    print("🔐 Telegram authentication mode:")

    if STRING_SESSION:
        print("   StringSession")
        print("   ✅ TELEGRAM_SESSION_STRING found")
    else:
        print("   File session")

    executed = load_executed()

    print()
    print(f"Loaded {len(executed)} previously executed signals.")

    # --------------------------------------------------------
    # METAAPI
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CONNECTING TO METAAPI")
    print("=" * 70)

    metaapi = MetaApi(METAAPI_TOKEN)

    account = await metaapi.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )

    print("✅ MetaApi SDK initialized")
    print(f"✅ Account found: {account.login}")
    print(f"   Server: {account.server}")
    print(f"   State: {account.state}")

    if "demo" not in account.server.lower():

        raise RuntimeError(
            "Safety check failed: account is not a demo account."
        )

    print("🟢 DEMO ACCOUNT CONFIRMED")

    await account.wait_connected()

    connection = account.get_rpc_connection()

    await connection.connect()
    await connection.wait_synchronized()

    print("✅ MT5 ACCOUNT CONNECTED")
    print("✅ RPC connection established")
    print("✅ MT5 ACCOUNT SYNCHRONIZED")

    symbol_spec = await connection.get_symbol_specification(SYMBOL)

    print()
    print(f"✅ {SYMBOL} available")
    print(f"   Digits: {symbol_spec.digits}")
    print(f"   Min volume: {symbol_spec.min_volume}")
    print(f"   Volume step: {symbol_spec.volume_step}")

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CONNECTING TO TELEGRAM")
    print("=" * 70)

    await client.connect()

    if not await client.is_user_authorized():

        raise RuntimeError(
            "Telegram session is not authorized."
        )

    print("✅ TELEGRAM SESSION AUTHORIZED")

    print()
    print("=" * 70)
    print("RESOLVING TELEGRAM SOURCES")
    print("=" * 70)

    source_ids = set()
    source_names = {}

    for source in SOURCE_CHANNELS:

        print()
        print(f"🔍 {source}")

        try:

            entity = await client.get_entity(source)

            peer_id = entity.id

            source_ids.add(peer_id)

            title = getattr(entity, "title", str(source))

            source_names[peer_id] = title

            print("   ✅ ACCESSIBLE")
            print(f"   Name: {title}")
            print(f"   ID: {peer_id}")

        except (
            UsernameInvalidError,
            UsernameNotOccupiedError,
            ValueError
        ) as e:

            print(f"   ❌ FAILED: {e}")

    print()
    print(f"Accessible sources: {len(source_ids)}/{len(SOURCE_CHANNELS)}")

    print()
    print("MONITORED NUMERIC CHAT IDS:")

    for chat_id in sorted(source_ids):

        print(
            f"  • {chat_id} -> "
            f"{source_names.get(chat_id, 'Unknown')}"
        )

    # --------------------------------------------------------
    # HANDLER
    # --------------------------------------------------------

    async def handle_message(event):

        try:

            print()
            print("=" * 70)
            print("📡 TELEGRAM UPDATE RECEIVED")
            print("=" * 70)

            print(f"Raw chat ID: {event.chat_id}")

            chat_id = event.chat_id

            # Telethon sometimes returns signed channel IDs.
            # Normalize to the entity ID.
            normalized_id = abs(chat_id)

            print(f"Normalized chat ID: {normalized_id}")

            if normalized_id not in source_ids:

                print("ℹ️ Message ignored - not a monitored source.")
                return

            print("✅ SOURCE CHANNEL MATCHED")

            message = event.message

            text = message.message

            if not text:
                print("ℹ️ Empty message ignored.")
                return

            channel_name = source_names.get(
                normalized_id,
                "Unknown"
            )

            print()
            print("=" * 70)
            print("📨 NEW TELEGRAM MESSAGE")
            print("=" * 70)

            print(f"Channel: {channel_name}")
            print(f"Message ID: {message.id}")

            print()
            print("RAW MESSAGE")
            print("-" * 70)
            print(text)
            print("-" * 70)

            signal = parse_signal(text)

            if not signal["parse_success"]:

                print("🔴 MESSAGE REJECTED BY PARSER")

                for error in signal["validation_errors"]:
                    print(f"   ❌ {error}")

                return

            print()
            print("🟢 SIGNAL PARSED SUCCESSFULLY")

            print(f"Direction: {signal['direction']}")
            print(
                f"Entry: "
                f"{signal['entry_low']} - "
                f"{signal['entry_high']}"
            )
            print(f"SL: {signal['stoploss']}")
            print(f"All TPs: {signal['tp_levels']}")

            tp_a, tp_b = choose_tp_mapping(
                channel_name,
                signal["tp_levels"]
            )

            if (
                tp_a not in signal["tp_levels"]
                or tp_b not in signal["tp_levels"]
            ):

                print("🔴 Required TP mapping missing.")
                return

            fingerprint = hashlib.sha256(
                f"{normalized_id}:{message.id}".encode()
            ).hexdigest()

            if fingerprint in executed:

                print("⚠️ Duplicate signal ignored.")
                return

            tick = await connection.get_symbol_price(SYMBOL)

            bid = tick["bid"]
            ask = tick["ask"]

            execution_price = (
                ask
                if signal["direction"] == "BUY"
                else bid
            )

            original_low = signal["entry_low"]
            original_high = signal["entry_high"]

            extended_low = original_low
            extended_high = original_high

            if signal["direction"] == "SELL":
                extended_low -= PRICE_EXTENSION
            else:
                extended_high += PRICE_EXTENSION

            inside_original = (
                original_low
                <= execution_price
                <= original_high
            )

            inside_extended = (
                extended_low
                <= execution_price
                <= extended_high
            )

            print()
            print("=" * 70)
            print("VALID SIGNAL RECEIVED FOR DEMO EXECUTION")
            print("=" * 70)

            print(f"Channel:   {channel_name}")
            print(f"Direction: {signal['direction']}")
            print(
                f"Entry:     "
                f"{original_low} - {original_high}"
            )
            print(f"SL:        {signal['stoploss']}")

            print()
            print(f"TP mapping: TP{tp_a} + TP{tp_b}")
            print(
                f"TP{tp_a}: "
                f"{signal['tp_levels'][tp_a]}"
            )
            print(
                f"TP{tp_b}: "
                f"{signal['tp_levels'][tp_b]}"
            )

            print()
            print(f"💰 {SYMBOL} BID: {bid}")
            print(f"💰 {SYMBOL} ASK: {ask}")

            print()
            print(
                f"Original entry range: "
                f"{original_low:.3f} - {original_high:.3f}"
            )
            print(
                f"30-pip extended range: "
                f"{extended_low:.3f} - {extended_high:.3f}"
            )
            print(
                f"Execution price: "
                f"{execution_price:.3f}"
            )

            if inside_original:

                print("Entry condition: ✅ INSIDE ORIGINAL RANGE")

            elif inside_extended:

                print("Entry condition: 🟡 OUTSIDE ORIGINAL RANGE")
                print("30-pip extension: ✅ ACCEPTED")

            else:

                print("Entry condition: ❌ OUTSIDE EXTENDED RANGE")
                print("⛔ No trade placed.")

                return

            order_type = (
                "ORDER_TYPE_BUY"
                if signal["direction"] == "BUY"
                else "ORDER_TYPE_SELL"
            )

            position_ids = []

            for index, tp_number in enumerate(
                (tp_a, tp_b),
                start=1
            ):

                print()
                print("-" * 70)
                print(f"🚀 EXECUTING POSITION {index}")

                result = await connection.create_market_order(
                    SYMBOL,
                    order_type,
                    LOT_SIZE,
                    {
                        "stopLoss": signal["stoploss"],
                        "takeProfit": signal["tp_levels"][tp_number],
                    }
                )

                print("📨 MetaApi result:")
                print(result)

                position_id = result.get("positionId")

                position_ids.append(position_id)

                print(
                    f"✅ POSITION {index} "
                    f"EXECUTED SUCCESSFULLY"
                )

                print(
                    f"   Position ID: {position_id}"
                )

            executed.add(fingerprint)
            save_executed(executed)

            print("✅ Executed signal memory saved")

            append_trade_log({
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "channel": channel_name,
                "direction": signal["direction"],
                "entry_low": original_low,
                "entry_high": original_high,
                "execution_price": execution_price,
                "stoploss": signal["stoploss"],
                "tp_numbers": [tp_a, tp_b],
                "position_ids": position_ids,
            })

            print("✅ Trade log saved")

            print()
            print("=" * 70)
            print("DEMO SIGNAL EXECUTION FINISHED")
            print("=" * 70)

        except Exception as e:

            print()
            print("❌ ERROR PROCESSING MESSAGE")
            print(repr(e))

    # --------------------------------------------------------
    # REGISTER GLOBAL LISTENER
    # --------------------------------------------------------

    client.add_event_handler(
        handle_message,
        events.NewMessage()
    )

    print()
    print("=" * 70)
    print("PHASE 6 DEMO EXECUTOR ACTIVE")
    print("=" * 70)

    print()
    print("Listening for ALL Telegram updates.")
    print("Messages are filtered using numeric chat IDs.")

    print()
    print("Waiting for Telegram signals...")
    print("Press CTRL+C to stop.")

    try:

        await client.run_until_disconnected()

    finally:

        await client.disconnect()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("🛑 Phase 6 stopped by user.")
