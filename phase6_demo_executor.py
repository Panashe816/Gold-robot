import asyncio
import os
import json
import hashlib
from datetime import datetime, timezone

import aiohttp
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from metaapi_cloud_sdk import MetaApi


# ============================================================
# PHASE 6 - DEMO TELEGRAM -> MT5 EXECUTOR
# ============================================================
#
# TELEGRAM
#     ↓
# PHASE 4 PARSER
#     ↓
# SIGNAL VALIDATION
#     ↓
# ORIGINAL ENTRY RANGE CHECK
#     ↓
# 30-PIP EXTENDED RANGE CHECK
#     ↓
# METAAPI
#     ↓
# WELTRADE DEMO MT5
#
# IMPORTANT:
# DEMO ONLY
#
# ============================================================


load_dotenv()


# ============================================================
# TELEGRAM USER API
# ============================================================

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")

TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")


# ============================================================
# TELEGRAM SESSION
# ============================================================
#
# RENDER:
#     Uses TELEGRAM_SESSION_STRING
#
# LOCAL COMPUTER:
#     Can still use the existing .session file
#
# ============================================================

TELEGRAM_SESSION_STRING = os.getenv(
    "TELEGRAM_SESSION_STRING"
)

TELEGRAM_SESSION = os.getenv(
    "TELEGRAM_SESSION",
    "gold_signal_bot"
)


# ============================================================
# TELEGRAM BOT NOTIFICATION
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_OUTPUT_CHANNEL_ID = os.getenv(
    "TELEGRAM_CHANNEL_ID",
    "-1002933896146"
)


# ============================================================
# METAAPI
# ============================================================

METAAPI_TOKEN = os.getenv(
    "METAAPI_TOKEN"
)

METAAPI_ACCOUNT_ID = os.getenv(
    "METAAPI_ACCOUNT_ID"
)


# ============================================================
# TRADING CONFIGURATION
# ============================================================

SYMBOL = "XAUUSD_i"

LOT_SIZE = 0.01

POSITIONS_PER_SIGNAL = 2

DEMO_ONLY = True


# ============================================================
# ENTRY EXTENSION
# ============================================================

ENTRY_EXTENSION_PIPS = 30

GOLD_PIP_SIZE = 0.1

ENTRY_EXTENSION_PRICE = (
    ENTRY_EXTENSION_PIPS * GOLD_PIP_SIZE
)


# ============================================================
# SIGNAL AGE
# ============================================================

MAX_SIGNAL_AGE_MINUTES = 20


# ============================================================
# SOURCE -> FIXED TP MAPPING
# ============================================================

TP_MAPPING = {

    "GOLD SIGNAL VIP": (3, 6),

    "GOLD HUNTER TRADE": (3, 4),

    "GOLD SIGNALS 98% SURE": (3, 4),

    "GOLD VIP SIGNALS INSIGHTS": (3, 6),
}


# ============================================================
# SOURCE CHANNELS
# ============================================================

SOURCE_CHANNELS = [

    "Goldhunterlearnttade3867",

    "GoldSignalVip110",

    "MrHenrys122",

    "AGoldvip_0786",

    # Test channel
    -1003170522699,
]


# ============================================================
# FILES
# ============================================================

EXECUTED_SIGNALS_FILE = (
    "phase6_executed_signals.json"
)

TRADE_LOG_FILE = (
    "phase6_trade_log.json"
)


# ============================================================
# GLOBALS
# ============================================================

metaapi = None

account = None

connection = None

executed_signals = set()

source_entities = []


# ============================================================
# LOAD EXECUTED SIGNALS
# ============================================================

def load_executed_signals():

    global executed_signals

    if not os.path.exists(
        EXECUTED_SIGNALS_FILE
    ):

        executed_signals = set()

        return

    try:

        with open(
            EXECUTED_SIGNALS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):

            executed_signals = set(
                str(item)
                for item in data
            )

        else:

            executed_signals = set()

    except Exception as e:

        print(
            f"⚠️ Could not load executed signals: {e}"
        )

        executed_signals = set()


# ============================================================
# SAVE EXECUTED SIGNALS
# ============================================================

def save_executed_signals():

    try:

        data = list(
            executed_signals
        )[-500:]

        with open(
            EXECUTED_SIGNALS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2
            )

        print(
            "✅ Executed signal memory saved"
        )

    except Exception as e:

        print(
            f"⚠️ Could not save executed signals: {e}"
        )


# ============================================================
# MAKE OBJECTS JSON SERIALIZABLE
# ============================================================

def make_json_safe(value):

    if value is None:

        return None

    if isinstance(
        value,
        (str, int, float, bool)
    ):

        return value

    if isinstance(
        value,
        datetime
    ):

        return value.isoformat()

    if isinstance(
        value,
        dict
    ):

        return {
            str(key): make_json_safe(val)
            for key, val in value.items()
        }

    if isinstance(
        value,
        (list, tuple)
    ):

        return [
            make_json_safe(item)
            for item in value
        ]

    return str(value)


# ============================================================
# TRADE LOG
# ============================================================

def save_trade_log(record):

    try:

        records = []

        if os.path.exists(
            TRADE_LOG_FILE
        ):

            with open(
                TRADE_LOG_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                try:

                    existing = json.load(f)

                    if isinstance(
                        existing,
                        list
                    ):

                        records = existing

                except Exception:

                    records = []

        safe_record = make_json_safe(
            record
        )

        records.append(
            safe_record
        )

        records = records[-1000:]

        with open(
            TRADE_LOG_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                records,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(
            "✅ Trade log saved"
        )

    except Exception as e:

        print(
            f"⚠️ Trade log error: {e}"
        )


# ============================================================
# TELEGRAM BOT NOTIFICATION
# ============================================================

async def send_notification(message):

    if not TELEGRAM_BOT_TOKEN:

        print(
            "ℹ️ Telegram bot token not configured"
        )

        return

    try:

        url = (
            "https://api.telegram.org/bot"
            f"{TELEGRAM_BOT_TOKEN}"
            "/sendMessage"
        )

        payload = {

            "chat_id":
                TELEGRAM_OUTPUT_CHANNEL_ID,

            "text":
                str(message),
        }

        async with aiohttp.ClientSession() as session:

            async with session.post(
                url,
                json=payload,
                timeout=10
            ) as response:

                if response.status != 200:

                    print(
                        "⚠️ Telegram notification failed:"
                    )

                    print(
                        await response.text()
                    )

                else:

                    print(
                        "✅ Telegram notification sent"
                    )

    except Exception as e:

        print(
            f"⚠️ Telegram notification error: {e}"
        )


# ============================================================
# NORMALIZE CHANNEL NAME
# ============================================================

def normalize_channel_name(name):

    if not name:

        return ""

    name = str(name).upper()

    replacements = {

        "𝗚": "G",
        "𝗢": "O",
        "𝗟": "L",
        "𝗗": "D",

        "𝐆": "G",
        "𝐎": "O",
        "𝐋": "L",
        "𝐃": "D",

        "𝗛": "H",
        "𝗨": "U",
        "𝗡": "N",
        "𝗧": "T",
        "𝗘": "E",
        "𝗥": "R",

        "𝗦": "S",
        "𝗜": "I",
        "𝗔": "A",
        "𝗩": "V",
        "𝗣": "P",

        "😎": "",
    }

    for old, new in replacements.items():

        name = name.replace(
            old,
            new
        )

    return " ".join(
        name.split()
    )


# ============================================================
# FIND TP MAPPING
# ============================================================

def get_tp_mapping(
    channel_name,
    signal=None
):

    normalized = normalize_channel_name(
        channel_name
    )

    # --------------------------------------------------------
    # GUNS THE TRADER
    # --------------------------------------------------------

    if (
        "GUNS" in normalized
        and "TRADER" in normalized
    ):

        if signal:

            tp_levels = signal.get(
                "tp_levels",
                {}
            )

            if isinstance(
                tp_levels,
                dict
            ):

                if 6 in tp_levels:

                    return (3, 6)

                if 4 in tp_levels:

                    return (3, 4)

        return None

    # --------------------------------------------------------
    # DIRECT MAPPING
    # --------------------------------------------------------

    if normalized in TP_MAPPING:

        return TP_MAPPING[
            normalized
        ]

    # --------------------------------------------------------
    # GOLD SIGNAL VIP
    # --------------------------------------------------------

    if (
        "GOLD" in normalized
        and "SIGNAL" in normalized
        and "VIP" in normalized
        and "HUNTER" not in normalized
        and "INSIGHTS" not in normalized
    ):

        return (3, 6)

    # --------------------------------------------------------
    # GOLD HUNTER TRADE
    # --------------------------------------------------------

    if (
        "HUNTER" in normalized
        and "TRADE" in normalized
    ):

        return (3, 4)

    # --------------------------------------------------------
    # GOLD SIGNALS 98% SURE
    # --------------------------------------------------------

    if (
        "98%" in normalized
        and "SURE" in normalized
    ):

        return (3, 4)

    # --------------------------------------------------------
    # GOLD VIP SIGNALS INSIGHTS
    # --------------------------------------------------------

    if "INSIGHTS" in normalized:

        return (3, 6)

    return None


# ============================================================
# SIGNAL UNIQUE ID
# ============================================================

def create_signal_id(signal):

    values = [

        str(
            signal.get(
                "channel",
                ""
            )
        ),

        str(
            signal.get(
                "message_id",
                ""
            )
        ),

        str(
            signal.get(
                "direction",
                ""
            )
        ),

        str(
            signal.get(
                "entry_low",
                ""
            )
        ),

        str(
            signal.get(
                "entry_high",
                ""
            )
        ),

        str(
            signal.get(
                "stoploss",
                ""
            )
        ),
    ]

    raw = "|".join(values)

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# SIGNAL AGE
# ============================================================

def signal_is_too_old(signal):

    timestamp = signal.get(
        "timestamp"
    )

    if not timestamp:

        return False

    try:

        if isinstance(
            timestamp,
            str
        ):

            signal_time = (
                datetime.fromisoformat(
                    timestamp.replace(
                        "Z",
                        "+00:00"
                    )
                )
            )

        else:

            signal_time = timestamp

        if signal_time.tzinfo is None:

            signal_time = (
                signal_time.replace(
                    tzinfo=timezone.utc
                )
            )

        now = datetime.now(
            timezone.utc
        )

        age = (
            now
            - signal_time.astimezone(
                timezone.utc
            )
        ).total_seconds() / 60

        print(
            f"⏱ Signal age: {age:.2f} minutes"
        )

        return (
            age >
            MAX_SIGNAL_AGE_MINUTES
        )

    except Exception as e:

        print(
            f"⚠️ Could not determine signal age: {e}"
        )

        return False


# ============================================================
# VALIDATE TRADE VALUES
# ============================================================

def validate_trade_values(
    direction,
    entry_low,
    entry_high,
    stoploss,
    tp1,
    tp2
):

    try:

        entry_low = float(
            entry_low
        )

        entry_high = float(
            entry_high
        )

        stoploss = float(
            stoploss
        )

        tp1 = float(tp1)

        tp2 = float(tp2)

    except Exception:

        return (
            False,
            "Non-numeric trade values"
        )

    if entry_low > entry_high:

        entry_low, entry_high = (
            entry_high,
            entry_low
        )

    direction = str(
        direction
    ).upper()

    if direction == "BUY":

        if stoploss >= entry_low:

            return (
                False,
                "BUY SL is not below entry"
            )

        if tp1 <= entry_high:

            return (
                False,
                "BUY TP1 is not above entry"
            )

        if tp2 <= entry_high:

            return (
                False,
                "BUY TP2 is not above entry"
            )

    elif direction == "SELL":

        if stoploss <= entry_high:

            return (
                False,
                "SELL SL is not above entry"
            )

        if tp1 >= entry_low:

            return (
                False,
                "SELL TP1 is not below entry"
            )

        if tp2 >= entry_low:

            return (
                False,
                "SELL TP2 is not below entry"
            )

    else:

        return (
            False,
            "Unknown direction"
        )

    return (
        True,
        "OK"
    )


# ============================================================
# METAAPI CONNECTION
# ============================================================

async def connect_metaapi():

    global metaapi
    global account
    global connection

    print()
    print("=" * 70)
    print("CONNECTING TO METAAPI")
    print("=" * 70)

    if not METAAPI_TOKEN:

        raise RuntimeError(
            "METAAPI_TOKEN missing"
        )

    if not METAAPI_ACCOUNT_ID:

        raise RuntimeError(
            "METAAPI_ACCOUNT_ID missing"
        )

    metaapi = MetaApi(
        METAAPI_TOKEN
    )

    print(
        "✅ MetaApi SDK initialized"
    )

    account = await (
        metaapi
        .metatrader_account_api
        .get_account(
            METAAPI_ACCOUNT_ID
        )
    )

    print(
        f"✅ Account found: "
        f"{account.name}"
    )

    print(
        f"   Server: "
        f"{account.server}"
    )

    print(
        f"   State: "
        f"{account.state}"
    )

    # --------------------------------------------------------
    # DEMO SAFETY
    # --------------------------------------------------------

    if DEMO_ONLY:

        server_name = str(
            account.server or ""
        ).lower()

        if "demo" not in server_name:

            raise RuntimeError(
                "🛑 DEMO-ONLY SAFETY CHECK FAILED.\n"
                f"Account server is: "
                f"{account.server}\n"
                "No trade will be placed."
            )

        print(
            "🟢 DEMO ACCOUNT CONFIRMED"
        )

    # --------------------------------------------------------
    # DEPLOY
    # --------------------------------------------------------

    if account.state != "DEPLOYED":

        print(
            "🔄 Account is not deployed."
        )

        await account.deploy()

        print(
            "✅ Deployment requested"
        )

    print(
        "⏳ Waiting for MT5 connection..."
    )

    await account.wait_connected()

    print(
        "✅ MT5 ACCOUNT CONNECTED"
    )

    # --------------------------------------------------------
    # RPC
    # --------------------------------------------------------

    connection = (
        account.get_rpc_connection()
    )

    await connection.connect()

    print(
        "✅ RPC connection established"
    )

    await connection.wait_synchronized()

    print(
        "✅ MT5 ACCOUNT SYNCHRONIZED"
    )

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    spec = await (
        connection
        .get_symbol_specification(
            SYMBOL
        )
    )

    if not spec:

        raise RuntimeError(
            f"Symbol {SYMBOL} not available"
        )

    print()
    print(
        f"✅ {SYMBOL} available"
    )

    print(
        f"   Digits: "
        f"{spec.get('digits')}"
    )

    print(
        f"   Min volume: "
        f"{spec.get('minVolume')}"
    )

    print(
        f"   Volume step: "
        f"{spec.get('volumeStep')}"
    )


# ============================================================
# GET LIVE PRICE
# ============================================================

async def get_live_price():

    price = await (
        connection
        .get_symbol_price(
            SYMBOL
        )
    )

    if not price:

        raise RuntimeError(
            f"No live price available "
            f"for {SYMBOL}"
        )

    bid = float(
        price["bid"]
    )

    ask = float(
        price["ask"]
    )

    print()
    print(
        f"💰 {SYMBOL} BID: "
        f"{bid:.3f}"
    )

    print(
        f"💰 {SYMBOL} ASK: "
        f"{ask:.3f}"
    )

    return bid, ask


# ============================================================
# CALCULATE EXECUTION RANGE
# ============================================================

def calculate_execution_range(
    direction,
    entry_low,
    entry_high
):

    entry_low = float(
        entry_low
    )

    entry_high = float(
        entry_high
    )

    if entry_low > entry_high:

        entry_low, entry_high = (
            entry_high,
            entry_low
        )

    direction = str(
        direction
    ).upper()

    original_low = entry_low

    original_high = entry_high

    extended_low = original_low

    extended_high = original_high

    if direction == "SELL":

        extended_low = (
            original_low
            - ENTRY_EXTENSION_PRICE
        )

    elif direction == "BUY":

        extended_high = (
            original_high
            + ENTRY_EXTENSION_PRICE
        )

    return (
        original_low,
        original_high,
        extended_low,
        extended_high
    )


# ============================================================
# CHECK ENTRY RANGE
# ============================================================

def price_inside_entry_range(
    direction,
    entry_low,
    entry_high,
    bid,
    ask
):

    (
        original_low,
        original_high,
        extended_low,
        extended_high
    ) = calculate_execution_range(
        direction,
        entry_low,
        entry_high
    )

    direction = str(
        direction
    ).upper()

    market_price = (
        ask
        if direction == "BUY"
        else bid
    )

    original_inside = (
        original_low
        <= market_price
        <= original_high
    )

    extended_inside = (
        extended_low
        <= market_price
        <= extended_high
    )

    print()
    print(
        f"Original entry range: "
        f"{original_low:.3f}"
        f" - "
        f"{original_high:.3f}"
    )

    print(
        f"30-pip extended range: "
        f"{extended_low:.3f}"
        f" - "
        f"{extended_high:.3f}"
    )

    print(
        f"Execution price: "
        f"{market_price:.3f}"
    )

    if original_inside:

        print(
            "Entry condition: "
            "✅ INSIDE ORIGINAL RANGE"
        )

        return (
            True,
            market_price,
            original_low,
            original_high,
            False
        )

    if extended_inside:

        print(
            "Entry condition: "
            "🟡 OUTSIDE ORIGINAL RANGE"
        )

        print(
            "30-pip extension: "
            "✅ ACCEPTED"
        )

        return (
            True,
            market_price,
            extended_low,
            extended_high,
            True
        )

    print(
        "Entry condition: "
        "❌ OUTSIDE EXTENDED RANGE"
    )

    return (
        False,
        market_price,
        extended_low,
        extended_high,
        True
    )


# ============================================================
# EXECUTE ONE POSITION
# ============================================================

async def execute_position(
    signal,
    tp_number,
    tp_price,
    position_number
):

    direction = str(
        signal["direction"]
    ).upper()

    stoploss = float(
        signal["stoploss"]
    )

    tp_price = float(
        tp_price
    )

    print()
    print("-" * 70)

    print(
        f"🚀 EXECUTING POSITION "
        f"{position_number}"
    )

    print(
        f"Direction: {direction}"
    )

    print(
        f"Symbol:    {SYMBOL}"
    )

    print(
        f"Volume:    {LOT_SIZE}"
    )

    print(
        f"SL:        {stoploss}"
    )

    print(
        f"TP{tp_number}:      "
        f"{tp_price}"
    )

    try:

        if direction == "BUY":

            result = await (
                connection
                .create_market_buy_order(
                    SYMBOL,
                    LOT_SIZE,
                    stop_loss=stoploss,
                    take_profit=tp_price
                )
            )

        elif direction == "SELL":

            result = await (
                connection
                .create_market_sell_order(
                    SYMBOL,
                    LOT_SIZE,
                    stop_loss=stoploss,
                    take_profit=tp_price
                )
            )

        else:

            print(
                "❌ Invalid trade direction"
            )

            return None

        print()
        print(
            "📨 MetaApi result:"
        )

        print(
            result
        )

        if isinstance(
            result,
            dict
        ):

            code = result.get(
                "stringCode"
            )

            if code == "TRADE_RETCODE_DONE":

                print()
                print(
                    f"✅ POSITION "
                    f"{position_number} "
                    f"EXECUTED SUCCESSFULLY"
                )

                position_id = (
                    result.get(
                        "positionId"
                    )
                )

                if position_id:

                    print(
                        f"   Position ID: "
                        f"{position_id}"
                    )

                return result

        print(
            f"⚠️ Position "
            f"{position_number} "
            f"returned unexpected result"
        )

        return None

    except Exception as e:

        print(
            f"❌ Position "
            f"{position_number} failed: "
            f"{e}"
        )

        return None


# ============================================================
# EXECUTE COMPLETE SIGNAL
# ============================================================

async def execute_signal(
    signal,
    message_id=None
):

    channel_name = signal.get(
        "channel",
        "Unknown"
    )

    print()
    print("=" * 70)
    print(
        "VALID SIGNAL RECEIVED "
        "FOR DEMO EXECUTION"
    )
    print("=" * 70)

    print(
        f"Channel:   "
        f"{channel_name}"
    )

    print(
        f"Direction: "
        f"{signal.get('direction')}"
    )

    print(
        f"Entry:     "
        f"{signal.get('entry_low')}"
        f" - "
        f"{signal.get('entry_high')}"
    )

    print(
        f"SL:        "
        f"{signal.get('stoploss')}"
    )

    # --------------------------------------------------------
    # TP MAPPING
    # --------------------------------------------------------

    mapping = get_tp_mapping(
        channel_name,
        signal
    )

    if not mapping:

        print(
            "❌ No TP mapping exists "
            "for this signal."
        )

        await send_notification(
            "🔴 SIGNAL REJECTED\n"
            f"Channel: {channel_name}\n"
            "Reason: No TP mapping"
        )

        return

    (
        tp_number_1,
        tp_number_2
    ) = mapping

    tp1 = signal.get(
        f"tp{tp_number_1}"
    )

    tp2 = signal.get(
        f"tp{tp_number_2}"
    )

    print()
    print(
        f"TP mapping: "
        f"TP{tp_number_1} + "
        f"TP{tp_number_2}"
    )

    print(
        f"TP{tp_number_1}: "
        f"{tp1}"
    )

    print(
        f"TP{tp_number_2}: "
        f"{tp2}"
    )

    # --------------------------------------------------------
    # REQUIRED VALUES
    # --------------------------------------------------------

    required = [

        signal.get(
            "direction"
        ),

        signal.get(
            "entry_low"
        ),

        signal.get(
            "entry_high"
        ),

        signal.get(
            "stoploss"
        ),

        tp1,

        tp2,
    ]

    if any(
        value is None
        for value in required
    ):

        print(
            "❌ Required trading value missing."
        )

        await send_notification(
            "🔴 SIGNAL REJECTED\n"
            f"Channel: {channel_name}\n"
            "Reason: Missing "
            "entry/SL/required TP"
        )

        return

    # --------------------------------------------------------
    # SIGNAL AGE
    # --------------------------------------------------------

    if signal_is_too_old(
        signal
    ):

        print(
            "❌ Signal is too old."
        )

        await send_notification(
            "🕒 SIGNAL EXPIRED\n"
            f"Channel: {channel_name}"
        )

        return

    # --------------------------------------------------------
    # VALUE VALIDATION
    # --------------------------------------------------------

    valid, reason = (
        validate_trade_values(
            signal["direction"],
            signal["entry_low"],
            signal["entry_high"],
            signal["stoploss"],
            tp1,
            tp2
        )
    )

    if not valid:

        print(
            f"❌ Signal rejected: "
            f"{reason}"
        )

        await send_notification(
            "🔴 SIGNAL REJECTED\n"
            f"Channel: {channel_name}\n"
            f"Reason: {reason}"
        )

        return

    # --------------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------------

    signal_for_id = {
        **signal,
        "message_id": message_id
    }

    signal_id = create_signal_id(
        signal_for_id
    )

    if signal_id in executed_signals:

        print(
            "⚠️ Signal already executed."
        )

        return

    # --------------------------------------------------------
    # LIVE PRICE
    # --------------------------------------------------------

    try:

        bid, ask = (
            await get_live_price()
        )

    except Exception as e:

        print(
            f"❌ Could not get live price: "
            f"{e}"
        )

        await send_notification(
            "❌ TRADE BLOCKED\n"
            f"Channel: {channel_name}\n"
            "Reason: Live price unavailable\n"
            f"{e}"
        )

        return

    # --------------------------------------------------------
    # ENTRY RANGE
    # --------------------------------------------------------

    (
        inside,
        market_price,
        execution_low,
        execution_high,
        extension_used
    ) = price_inside_entry_range(
        signal["direction"],
        signal["entry_low"],
        signal["entry_high"],
        bid,
        ask
    )

    if not inside:

        print()
        print(
            "⛔ No trade placed."
        )

        await send_notification(

            "⏳ SIGNAL RECEIVED — "
            "OUTSIDE EXECUTION RANGE\n"
            "────────────────\n"
            f"📺 Channel: {channel_name}\n"
            f"💎 Symbol: {SYMBOL}\n"
            f"🎯 Direction: "
            f"{signal['direction']}\n"
            f"📍 Original Entry: "
            f"{signal['entry_low']} - "
            f"{signal['entry_high']}\n"
            f"📍 Extended Entry: "
            f"{execution_low:.3f} - "
            f"{execution_high:.3f}\n"
            f"💰 Current price: "
            f"{market_price:.3f}\n"
            f"🛑 SL: "
            f"{signal['stoploss']}\n"
            f"🎯 TP{tp_number_1}: "
            f"{tp1}\n"
            f"🎯 TP{tp_number_2}: "
            f"{tp2}\n"
        )

        return

    # --------------------------------------------------------
    # FINAL DEMO SAFETY
    # --------------------------------------------------------

    if DEMO_ONLY:

        server_name = str(
            account.server or ""
        ).lower()

        if "demo" not in server_name:

            print(
                "🛑 DEMO SAFETY CHECK FAILED"
            )

            return

    # --------------------------------------------------------
    # EXTENSION STATUS
    # --------------------------------------------------------

    if extension_used:

        print()
        print(
            "🟡 30-PIP ENTRY EXTENSION USED"
        )

        print(
            f"Original range: "
            f"{signal['entry_low']}"
            f" - "
            f"{signal['entry_high']}"
        )

        print(
            f"Execution range: "
            f"{execution_low:.3f}"
            f" - "
            f"{execution_high:.3f}"
        )

    else:

        print()
        print(
            "🟢 ORIGINAL ENTRY RANGE USED"
        )

    # --------------------------------------------------------
    # POSITION 1
    # --------------------------------------------------------

    result_1 = await execute_position(
        signal,
        tp_number_1,
        tp1,
        1
    )

    if not result_1:

        print(
            "❌ Position 1 failed."
        )

        await send_notification(
            "❌ DEMO TRADE FAILED\n"
            f"Channel: {channel_name}\n"
            "Position 1 could not be executed."
        )

        return

    # --------------------------------------------------------
    # POSITION 2
    # --------------------------------------------------------

    result_2 = await execute_position(
        signal,
        tp_number_2,
        tp2,
        2
    )

    if not result_2:

        print(
            "❌ Position 2 failed."
        )

        print(
            "⚠️ Position 1 was already "
            "successfully executed."
        )

        await send_notification(
            "⚠️ PARTIAL DEMO EXECUTION\n"
            f"Channel: {channel_name}\n"
            "Position 1: EXECUTED\n"
            "Position 2: FAILED"
        )

        return

    # --------------------------------------------------------
    # BOTH POSITIONS SUCCESSFUL
    # --------------------------------------------------------

    executed_signals.add(
        signal_id
    )

    save_executed_signals()

    # --------------------------------------------------------
    # TRADE LOG
    # --------------------------------------------------------

    record = {

        "signal_id":
            signal_id,

        "time":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "channel":
            channel_name,

        "message_id":
            message_id,

        "direction":
            signal["direction"],

        "symbol":
            SYMBOL,

        "original_entry_low":
            signal["entry_low"],

        "original_entry_high":
            signal["entry_high"],

        "execution_range_low":
            execution_low,

        "execution_range_high":
            execution_high,

        "extension_pips":
            ENTRY_EXTENSION_PIPS,

        "extension_used":
            extension_used,

        "execution_price":
            market_price,

        "stoploss":
            signal["stoploss"],

        "position_1": {

            "tp_number":
                tp_number_1,

            "tp":
                tp1,

            "volume":
                LOT_SIZE,

            "result":
                result_1,
        },

        "position_2": {

            "tp_number":
                tp_number_2,

            "tp":
                tp2,

            "volume":
                LOT_SIZE,

            "result":
                result_2,
        },
    }

    save_trade_log(
        record
    )

    # --------------------------------------------------------
    # NOTIFICATION
    # --------------------------------------------------------

    if extension_used:

        range_status = (
            "🟡 30-PIP EXTENSION USED"
        )

    else:

        range_status = (
            "🟢 ORIGINAL RANGE"
        )

    message = (

        "🟢 DEMO TRADE EXECUTED\n"

        "────────────────\n"

        f"📺 Channel: "
        f"{channel_name}\n"

        f"💎 Symbol: "
        f"{SYMBOL}\n"

        f"🎯 Direction: "
        f"{signal['direction']}\n"

        f"💰 Execution: "
        f"{market_price:.3f}\n"

        f"📍 Original Entry: "
        f"{signal['entry_low']} - "
        f"{signal['entry_high']}\n"

        f"📍 Execution Range: "
        f"{execution_low:.3f} - "
        f"{execution_high:.3f}\n"

        f"{range_status}\n"

        f"🛑 SL: "
        f"{signal['stoploss']}\n"

        f"🎯 Position 1: "
        f"TP{tp_number_1} = "
        f"{tp1}\n"

        f"   Volume: "
        f"{LOT_SIZE}\n"

        f"🎯 Position 2: "
        f"TP{tp_number_2} = "
        f"{tp2}\n"

        f"   Volume: "
        f"{LOT_SIZE}\n"

        f"💰 Total volume: "
        f"{LOT_SIZE * 2:.2f}\n"

        "🟢 DEMO ACCOUNT"
    )

    await send_notification(
        message
    )

    print()
    print("=" * 70)
    print(
        "DEMO SIGNAL EXECUTION FINISHED"
    )
    print("=" * 70)


# ============================================================
# HANDLE TELEGRAM MESSAGE
# ============================================================

async def handle_message(event):

    try:

        message = event.message

        if not message:

            return

        text = message.message

        if not text:

            return

        chat = await event.get_chat()

        channel_name = (
            getattr(
                chat,
                "title",
                None
            )
            or
            getattr(
                chat,
                "username",
                None
            )
            or
            "Unknown"
        )

        print()
        print("=" * 70)
        print(
            "📨 NEW TELEGRAM MESSAGE"
        )
        print("=" * 70)

        print(
            f"Channel: "
            f"{channel_name}"
        )

        print(
            f"Message ID: "
            f"{message.id}"
        )

        print()
        print(
            "RAW MESSAGE"
        )

        print("-" * 70)

        print(text)

        print("-" * 70)

        # ----------------------------------------------------
        # PHASE 4 PARSER
        # ----------------------------------------------------

        from phase4_live_parser import (
            parse_signal
        )

        signal = parse_signal(
            text,
            channel_name
        )

        if not signal:

            print(
                "🔴 Parser returned no signal."
            )

            return

        if not signal.get(
            "parse_success",
            False
        ):

            print(
                "🔴 MESSAGE REJECTED BY PARSER"
            )

            for error in signal.get(
                "validation_errors",
                []
            ):

                print(
                    f"   ❌ {error}"
                )

            return

        # ----------------------------------------------------
        # METADATA
        # ----------------------------------------------------

        signal["message_id"] = (
            message.id
        )

        print()
        print(
            "🟢 SIGNAL PARSED SUCCESSFULLY"
        )

        print(
            f"Direction: "
            f"{signal.get('direction')}"
        )

        print(
            f"Entry: "
            f"{signal.get('entry_low')}"
            f" - "
            f"{signal.get('entry_high')}"
        )

        print(
            f"SL: "
            f"{signal.get('stoploss')}"
        )

        print(
            f"All TPs: "
            f"{signal.get('tp_levels')}"
        )

        # ----------------------------------------------------
        # EXECUTE
        # ----------------------------------------------------

        await execute_signal(
            signal,
            message.id
        )

    except Exception as e:

        print()
        print(
            f"❌ Message handler error: "
            f"{e}"
        )

        try:

            await send_notification(
                "❌ PHASE 6 ERROR\n"
                f"{str(e)[:500]}"
            )

        except Exception:

            pass


# ============================================================
# RESOLVE TELEGRAM SOURCES
# ============================================================

async def resolve_sources(
    client
):

    global source_entities

    print()
    print("=" * 70)
    print(
        "RESOLVING TELEGRAM SOURCES"
    )
    print("=" * 70)

    source_entities = []

    for source in SOURCE_CHANNELS:

        try:

            print()
            print(
                f"🔍 {source}"
            )

            entity = await client.get_entity(
                source
            )

            source_entities.append(
                entity
            )

            print(
                "   ✅ ACCESSIBLE"
            )

            print(
                f"   Name: "
                f"{getattr(entity, 'title', 'Unknown')}"
            )

            print(
                f"   ID: "
                f"{getattr(entity, 'id', 'Unknown')}"
            )

        except Exception as e:

            print(
                f"   ❌ FAILED: {e}"
            )

    print()
    print(
        f"Accessible sources: "
        f"{len(source_entities)}"
        f"/"
        f"{len(SOURCE_CHANNELS)}"
    )


# ============================================================
# PRINT TP RULES
# ============================================================

def print_tp_rules():

    print()
    print("=" * 70)
    print(
        "TP RULES"
    )
    print("=" * 70)

    print(
        "  • GOLD SIGNAL VIP → TP3 + TP6"
    )

    print(
        "  • GOLD HUNTER TRADE → TP3 + TP4"
    )

    print(
        "  • GOLD SIGNALS 98% SURE → TP3 + TP4"
    )

    print(
        "  • GOLD VIP SIGNALS INSIGHTS → TP3 + TP6"
    )

    print(
        "  • GUNS THE TRADER → dynamic"
    )

    print(
        "      4 TPs → TP3 + TP4"
    )

    print(
        "      6 TPs → TP3 + TP6"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 70)
    print(
        "PHASE 6 - DEMO TELEGRAM → MT5 EXECUTOR"
    )
    print("=" * 70)

    print()
    print(
        "⚠️ DEMO-ONLY MODE"
    )

    print(
        "⚠️ NO LIVE ACCOUNT TRADING ALLOWED"
    )

    print()

    print(
        f"Symbol: "
        f"{SYMBOL}"
    )

    print(
        f"Lot per position: "
        f"{LOT_SIZE}"
    )

    print(
        f"Positions per signal: "
        f"{POSITIONS_PER_SIGNAL}"
    )

    print(
        f"Entry extension: "
        f"{ENTRY_EXTENSION_PIPS} pips"
    )

    print(
        f"Price extension: "
        f"{ENTRY_EXTENSION_PRICE:.1f}"
    )

    print()

    # --------------------------------------------------------
    # CREDENTIAL CHECK
    # --------------------------------------------------------

    if not TELEGRAM_API_ID:

        print(
            "❌ TELEGRAM_API_ID "
            "missing"
        )

        return

    if not TELEGRAM_API_HASH:

        print(
            "❌ TELEGRAM_API_HASH "
            "missing"
        )

        return

    # --------------------------------------------------------
    # TELEGRAM SESSION CHECK
    # --------------------------------------------------------

    if TELEGRAM_SESSION_STRING:

        print(
            "🔐 Telegram authentication mode:"
        )

        print(
            "   StringSession"
        )

        print(
            "   ✅ TELEGRAM_SESSION_STRING found"
        )

    else:

        print(
            "🔐 Telegram authentication mode:"
        )

        print(
            "   Local .session file"
        )

        print(
            f"   Session: "
            f"{TELEGRAM_SESSION}"
        )

    # --------------------------------------------------------
    # LOAD MEMORY
    # --------------------------------------------------------

    load_executed_signals()

    print(
        f"Loaded "
        f"{len(executed_signals)} "
        "previously executed signals."
    )

    # --------------------------------------------------------
    # METAAPI
    # --------------------------------------------------------

    try:

        await connect_metaapi()

    except Exception as e:

        print()
        print("=" * 70)
        print(
            "❌ METAAPI CONNECTION FAILED"
        )
        print("=" * 70)

        print(
            e
        )

        return

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "CONNECTING TO TELEGRAM"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Render uses StringSession.
    #
    # Local computer can still use:
    # gold_signal_bot.session
    #
    # --------------------------------------------------------

    if TELEGRAM_SESSION_STRING:

        client = TelegramClient(

            StringSession(
                TELEGRAM_SESSION_STRING
            ),

            int(
                TELEGRAM_API_ID
            ),

            TELEGRAM_API_HASH
        )

    else:

        client = TelegramClient(

            TELEGRAM_SESSION,

            int(
                TELEGRAM_API_ID
            ),

            TELEGRAM_API_HASH
        )

    try:

        await client.start()

        print(
            "✅ TELEGRAM SESSION AUTHORIZED"
        )

        # ----------------------------------------------------
        # RESOLVE SOURCES
        # ----------------------------------------------------

        await resolve_sources(
            client
        )

        if not source_entities:

            print()
            print(
                "❌ No Telegram sources accessible."
            )

            return

        # ----------------------------------------------------
        # REGISTER HANDLER
        # ----------------------------------------------------

        client.add_event_handler(

            handle_message,

            events.NewMessage(
                chats=source_entities
            )
        )

        # ----------------------------------------------------
        # ACTIVE
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print(
            "PHASE 6 DEMO EXECUTOR ACTIVE"
        )
        print("=" * 70)

        print()
        print(
            "MONITORING:"
        )

        for entity in source_entities:

            print(
                f"  • "
                f"{getattr(entity, 'title', 'Unknown')}"
            )

        print()

        print(
            "TRADE SETTINGS:"
        )

        print(
            f"  • Symbol: {SYMBOL}"
        )

        print(
            "  • Position 1: source TP mapping"
        )

        print(
            "  • Position 2: source TP mapping"
        )

        print(
            f"  • Volume: {LOT_SIZE} each"
        )

        print(
            "  • Same entry range"
        )

        print(
            "  • Same stop loss"
        )

        print(
            f"  • {ENTRY_EXTENSION_PIPS}-pip "
            "entry extension"
        )

        print(
            "  • DEMO ONLY"
        )

        print_tp_rules()

        print()
        print(
            "ENTRY EXTENSION RULE:"
        )

        print(
            f"  • SELL → lower boundary "
            f"- {ENTRY_EXTENSION_PRICE:.1f}"
        )

        print(
            f"  • BUY → upper boundary "
            f"+ {ENTRY_EXTENSION_PRICE:.1f}"
        )

        print()
        print(
            "Waiting for Telegram signals..."
        )

        print(
            "Press CTRL+C to stop."
        )

        try:

            await client.run_until_disconnected()

        except KeyboardInterrupt:

            print()
            print(
                "🛑 Phase 6 stopped by user."
            )

    finally:

        try:

            await client.disconnect()

        except Exception:

            pass

        try:

            if connection:

                await connection.close()

        except Exception:

            pass

        try:

            if metaapi:

                await metaapi.close()

        except Exception:

            pass


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "🛑 Phase 6 stopped by user."
        )