import asyncio
import json
import os
import re
from datetime import datetime, timezone

import aiohttp
from dotenv import load_dotenv
from telethon import TelegramClient, events, utils
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError
from telethon.sessions import StringSession
from metaapi_cloud_sdk import MetaApi


# ============================================================
# PHASE 6 - DEMO TELEGRAM -> MT5 EXECUTOR
# ============================================================
#
# DEMO ACCOUNT ONLY
#
# Telegram
#     â†“
# Signal parser
#     â†“
# Validation
#     â†“
# 30-pip entry extension
#     â†“
# MetaApi
#     â†“
# MT5 DEMO ACCOUNT
#
# NO LIVE ACCOUNT TRADING
#
# ============================================================


load_dotenv()


# ============================================================
# TELEGRAM CONFIGURATION
# ============================================================

API_ID = int(
    os.getenv(
        "TELEGRAM_API_ID",
        "14424659"
    )
)

API_HASH = os.getenv(
    "TELEGRAM_API_HASH",
    ""
)

TELEGRAM_SESSION_STRING = os.getenv(
    "TELEGRAM_SESSION_STRING",
    ""
)


# ============================================================
# METAAPI CONFIGURATION
# ============================================================

METAAPI_TOKEN = os.getenv(
    "METAAPI_TOKEN",
    ""
)

METAAPI_ACCOUNT_ID = os.getenv(
    "METAAPI_ACCOUNT_ID",
    ""
)


# ============================================================
# OPTIONAL TELEGRAM NOTIFICATION
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
)

TELEGRAM_NOTIFICATION_CHAT_ID = os.getenv(
    "TELEGRAM_NOTIFICATION_CHAT_ID",
    ""
)


# ============================================================
# TRADING SETTINGS
# ============================================================

SYMBOL = os.getenv(
    "TRADE_SYMBOL",
    "XAUUSD_i"
)

LOT_SIZE = float(
    os.getenv(
        "LOT_SIZE",
        "0.01"
    )
)

POSITIONS_PER_SIGNAL = 2


# ============================================================
# ENTRY EXTENSION
# ============================================================
#
# 30 pips on this XAUUSD setup = 3.0 price units.
#
# SELL:
#
# Original:
#     4630 - 4633
#
# Extended:
#     4627 - 4633
#
# BUY:
#
# Original:
#     4621 - 4624
#
# Extended:
#     4621 - 4627
#
# ============================================================

ENTRY_EXTENSION_PIPS = 30

ENTRY_EXTENSION_PRICE = float(
    os.getenv(
        "ENTRY_EXTENSION_PRICE",
        "3.0"
    )
)


# ============================================================
# FILES
# ============================================================

EXECUTED_FILE = (
    "phase6_executed_signals.json"
)

TRADE_LOG_FILE = (
    "phase6_trade_log.json"
)


# ============================================================
# TELEGRAM SOURCES
# ============================================================

SOURCE_CHANNELS = [

    "Goldhunterlearnttade3867",

    "GoldSignalVip110",

    "MrHenrys122",

    "AGoldvip_0786",

    # GUNS THE TRADER
    -1003170522699,
]


# ============================================================
# TP MAPPINGS
# ============================================================
#
# GOLD SIGNAL VIP:
#     TP3 + TP6
#
# GOLD HUNTER:
#     TP3 + TP4
#
# GOLD SIGNALS 98%:
#     TP3 + TP4
#
# GOLD VIP:
#     TP3 + TP6
#
# GUNS:
#     4 TPs -> TP3 + TP4
#     6 TPs -> TP3 + TP6
#
# ============================================================

TP_RULES = {

    "GOLD SIGNAL VIP": (
        3,
        6
    ),

    "GOLD HUNTER TRADE": (
        3,
        4
    ),

    "GOLD SIGNALS 98% SURE": (
        3,
        4
    ),

    "GOLD VIP SIGNALS INSIGHTS": (
        3,
        6
    ),
}


# ============================================================
# RUNTIME STATE
# ============================================================

resolved_sources = []

resolved_chat_ids = set()

source_names = {}

executed_signals = set()

metaapi = None

account = None

connection = None


# ============================================================
# TIME
# ============================================================

def now_iso():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# GENERIC OBJECT / DICT FIELD HELPER
# ============================================================
#
# MetaApi versions can return dictionaries or objects.
#
# This prevents:
#
#     AttributeError:
#     'dict' object has no attribute 'digits'
#
# ============================================================

def get_field(
    obj,
    field,
    default=None
):

    if isinstance(
        obj,
        dict
    ):

        return obj.get(
            field,
            default
        )

    return getattr(
        obj,
        field,
        default
    )


# ============================================================
# JSON HELPERS
# ============================================================

def load_json_list(
    path
):

    if not os.path.exists(
        path
    ):

        return []

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(
            data,
            list
        ):

            return data

        return []

    except Exception as error:

        print(
            f"âš ï¸ Could not read {path}: {error}"
        )

        return []


# ============================================================

def save_json(
    path,
    data
):

    temporary_file = (
        path + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            default=str
        )

    os.replace(
        temporary_file,
        path
    )


# ============================================================
# LOAD EXECUTION MEMORY
# ============================================================

def load_execution_memory():

    global executed_signals

    rows = load_json_list(
        EXECUTED_FILE
    )

    executed_signals = set()

    for row in rows:

        if isinstance(
            row,
            dict
        ):

            key = row.get(
                "signal_key"
            )

            if key:

                executed_signals.add(
                    str(key)
                )

        elif isinstance(
            row,
            str
        ):

            executed_signals.add(
                row
            )

    print(
        f"Loaded {len(executed_signals)} previously executed signals."
    )


# ============================================================
# SAVE EXECUTED SIGNAL
# ============================================================

def save_executed_signal(
    signal_key,
    signal,
    positions
):

    rows = load_json_list(
        EXECUTED_FILE
    )

    rows.append({

        "signal_key":
            signal_key,

        "timestamp":
            now_iso(),

        "channel":
            signal["channel"],

        "chat_id":
            signal["chat_id"],

        "message_id":
            signal["message_id"],

        "direction":
            signal["direction"],

        "entry_low":
            signal["entry_low"],

        "entry_high":
            signal["entry_high"],

        "execution_range_low":
            signal["execution_range_low"],

        "execution_range_high":
            signal["execution_range_high"],

        "execution_price":
            signal["execution_price"],

        "stoploss":
            signal["stoploss"],

        "tp_levels":
            signal["tp_levels"],

        "execution_tp_numbers":
            signal["execution_tp_numbers"],

        "execution_tps":
            signal["execution_tps"],

        "positions":
            positions,
    })

    save_json(
        EXECUTED_FILE,
        rows
    )

    executed_signals.add(
        signal_key
    )

    print(
        "âœ… Executed signal memory saved"
    )


# ============================================================
# TRADE LOG
# ============================================================

def save_trade_log(
    signal,
    positions
):

    rows = load_json_list(
        TRADE_LOG_FILE
    )

    rows.append({

        "timestamp":
            now_iso(),

        "channel":
            signal["channel"],

        "chat_id":
            signal["chat_id"],

        "message_id":
            signal["message_id"],

        "direction":
            signal["direction"],

        "symbol":
            SYMBOL,

        "volume":
            LOT_SIZE,

        "entry_low":
            signal["entry_low"],

        "entry_high":
            signal["entry_high"],

        "execution_range_low":
            signal["execution_range_low"],

        "execution_range_high":
            signal["execution_range_high"],

        "execution_price":
            signal["execution_price"],

        "stoploss":
            signal["stoploss"],

        "tp_levels":
            signal["tp_levels"],

        "execution_tp_numbers":
            signal["execution_tp_numbers"],

        "execution_tps":
            signal["execution_tps"],

        "positions":
            positions,
    })

    save_json(
        TRADE_LOG_FILE,
        rows
    )

    print(
        "âœ… Trade log saved"
    )


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(
    text
):

    if not text:

        return ""

    text = text.replace(
        "\r",
        "\n"
    )

    text = text.replace(
        "\u00A0",
        " "
    )

    return text.strip()


# ============================================================
# DIRECTION
# ============================================================

def extract_direction(
    text
):

    match = re.search(
        r"\b(BUY|SELL)\b",
        text.upper()
    )

    if match:

        return match.group(
            1
        )

    return None


# ============================================================
# ENTRY
# ============================================================

def extract_entry(
    text
):

    patterns = [

        # ENTRY: 4625 - 4636
        r"\bENTRY\b\s*[:=\-]?\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*[/_â€“â€”-]\s*"
        r"(\d+(?:\.\d+)?)",

        # GOLD SELL NOW 4630_4633
        r"\b(?:GOLD|XAUUSD|XAU)\b"
        r"\s+(?:BUY|SELL)\b"
        r"(?:\s+NOW)?"
        r"\s+"
        r"(\d+(?:\.\d+)?)"
        r"\s*[/_â€“â€”-]\s*"
        r"(\d+(?:\.\d+)?)",

        # BUY XAUUSD 4628/4636
        r"\b(?:BUY|SELL)\b"
        r"\s+(?:GOLD|XAUUSD|XAU)\b"
        r"(?:\s+NOW)?"
        r"\s+"
        r"(\d+(?:\.\d+)?)"
        r"\s*[/_â€“â€”-]\s*"
        r"(\d+(?:\.\d+)?)",

        # Generic fallback
        r"\b(\d+(?:\.\d+)?)"
        r"\s*[/_â€“â€”-]\s*"
        r"(\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:

            continue

        first = float(
            match.group(1)
        )

        second = float(
            match.group(2)
        )

        return (
            min(first, second),
            max(first, second)
        )

    return (
        None,
        None
    )


# ============================================================
# STOP LOSS
# ============================================================

def extract_sl(
    text
):

    pattern = (

        r"\b(?:SL|"
        r"STOP\s*LOSS|"
        r"STOPLOSS|"
        r"STOP)\b"

        r"\s*[:.=\-]?\s*"

        r"(\d+(?:\.\d+)?)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1)
        )

    return None


# ============================================================
# TAKE PROFITS
# ============================================================

def extract_tp_levels(
    text
):

    result = {}

    pattern = (

        r"\bTP\s*"

        r"([1-9]|1[0-9])"

        r"\s*[:.=\-]?\s*"

        r"(\d+(?:\.\d+)?)"
    )

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE
    )

    for number, price in matches:

        result[
            int(number)
        ] = float(price)

    return dict(
        sorted(
            result.items()
        )
    )


# ============================================================
# CANONICAL CHANNEL NAME
# ============================================================

def canonical_channel(
    name
):

    return " ".join(
        (name or "")
        .upper()
        .split()
    )


# ============================================================
# CHOOSE TP MAPPING
# ============================================================

def choose_tp_mapping(
    channel_name,
    tp_levels
):

    channel = canonical_channel(
        channel_name
    )

    # --------------------------------------------------------
    # GUNS THE TRADER - DYNAMIC
    # --------------------------------------------------------

    if (
        "GUNS THE TRADER"
        in channel
    ):

        if 6 in tp_levels:

            return (
                3,
                6
            )

        if 4 in tp_levels:

            return (
                3,
                4
            )

        return None

    # --------------------------------------------------------
    # FIXED SOURCE MAPPINGS
    # --------------------------------------------------------

    for source, mapping in TP_RULES.items():

        if source in channel:

            return mapping

    return None


# ============================================================
# VALIDATE SIGNAL
# ============================================================

def validate_signal(
    direction,
    entry_low,
    entry_high,
    stoploss,
    tp_levels,
    mapping
):

    errors = []

    if direction not in (
        "BUY",
        "SELL"
    ):

        errors.append(
            "Missing BUY/SELL direction"
        )

    if (
        entry_low is None
        or entry_high is None
    ):

        errors.append(
            "Missing entry"
        )

    if stoploss is None:

        errors.append(
            "Missing stop loss"
        )

    if not tp_levels:

        errors.append(
            "No TP levels found"
        )

    if mapping is None:

        errors.append(
            "No TP mapping available"
        )

    if errors:

        return (
            False,
            errors
        )

    # --------------------------------------------------------
    # PRICE RANGE
    # --------------------------------------------------------

    all_prices = [

        entry_low,

        entry_high,

        stoploss,

    ]

    all_prices.extend(
        tp_levels.values()
    )

    for price in all_prices:

        if not 1800 <= price <= 6000:

            errors.append(
                f"Price {price} outside Gold range"
            )

    # --------------------------------------------------------
    # REQUIRED MAPPED TPS
    # --------------------------------------------------------

    for tp_number in mapping:

        if tp_number not in tp_levels:

            errors.append(
                f"Missing mapped TP{tp_number}"
            )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if direction == "BUY":

        if stoploss >= entry_low:

            errors.append(
                f"BUY SL {stoploss} "
                f"is not below "
                f"entry {entry_low}"
            )

        first_tp = min(
            tp_levels.values()
        )

        if first_tp <= entry_high:

            errors.append(
                f"BUY TP {first_tp} "
                f"is not above "
                f"entry {entry_high}"
            )

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if direction == "SELL":

        if stoploss <= entry_high:

            errors.append(
                f"SELL SL {stoploss} "
                f"is not above "
                f"entry {entry_high}"
            )

        first_tp = max(
            tp_levels.values()
        )

        if first_tp >= entry_low:

            errors.append(
                f"SELL TP {first_tp} "
                f"is not below "
                f"entry {entry_low}"
            )

    # --------------------------------------------------------
    # ENTRY RANGE SANITY
    # --------------------------------------------------------

    if (
        entry_high - entry_low
        > 100
    ):

        errors.append(
            "Entry range too wide"
        )

    return (
        len(errors) == 0,
        errors
    )


# ============================================================
# PARSE SIGNAL
# ============================================================

def parse_signal(
    message,
    channel_name,
    chat_id,
    message_id
):

    text = normalize_text(
        message
    )

    direction = extract_direction(
        text
    )

    entry_low, entry_high = (
        extract_entry(text)
    )

    stoploss = extract_sl(
        text
    )

    tp_levels = extract_tp_levels(
        text
    )

    mapping = choose_tp_mapping(
        channel_name,
        tp_levels
    )

    valid, errors = validate_signal(
        direction,
        entry_low,
        entry_high,
        stoploss,
        tp_levels,
        mapping
    )

    execution_tps = {}

    if mapping:

        for tp_number in mapping:

            if tp_number in tp_levels:

                execution_tps[
                    tp_number
                ] = tp_levels[
                    tp_number
                ]

    return {

        "channel":
            channel_name,

        "chat_id":
            int(chat_id),

        "message_id":
            int(message_id),

        "direction":
            direction,

        "entry_low":
            entry_low,

        "entry_high":
            entry_high,

        "stoploss":
            stoploss,

        "tp_levels":
            tp_levels,

        "execution_tp_numbers":
            list(mapping)
            if mapping
            else [],

        "execution_tps":
            execution_tps,

        "parse_success":
            valid,

        "validation_errors":
            errors,

        "timestamp":
            now_iso(),
    }


# ============================================================
# METAAPI SYMBOL SPECIFICATION
# ============================================================

async def verify_symbol():

    specification = (
        await connection
        .get_symbol_specification(
            SYMBOL
        )
    )

    # IMPORTANT:
    # MetaApi can return either a dict
    # or an object depending on SDK/runtime.

    digits = get_field(
        specification,
        "digits",
        "Unknown"
    )

    min_volume = get_field(
        specification,
        "minVolume",
        None
    )

    if min_volume is None:

        min_volume = get_field(
            specification,
            "min_volume",
            "Unknown"
        )

    volume_step = get_field(
        specification,
        "volumeStep",
        None
    )

    if volume_step is None:

        volume_step = get_field(
            specification,
            "volume_step",
            "Unknown"
        )

    print()
    print(
        f"âœ… {SYMBOL} available"
    )

    print(
        f"   Digits: {digits}"
    )

    print(
        f"   Min volume: {min_volume}"
    )

    print(
        f"   Volume step: {volume_step}"
    )

    return specification


# ============================================================
# GET CURRENT PRICE
# ============================================================

async def get_current_price():

    price = (
        await connection
        .get_symbol_price(
            SYMBOL
        )
    )

    bid = get_field(
        price,
        "bid"
    )

    ask = get_field(
        price,
        "ask"
    )

    if bid is None or ask is None:

        raise RuntimeError(
            f"Could not obtain price: {price}"
        )

    return (
        float(bid),
        float(ask)
    )


# ============================================================
# CALCULATE EXTENDED RANGE
# ============================================================

def calculate_extended_range(
    direction,
    entry_low,
    entry_high
):

    # --------------------------------------------------------
    # SELL
    #
    # 4630 - 4633
    #
    # becomes
    #
    # 4627 - 4633
    # --------------------------------------------------------

    if direction == "SELL":

        return (
            entry_low
            - ENTRY_EXTENSION_PRICE,

            entry_high
        )

    # --------------------------------------------------------
    # BUY
    #
    # 4621 - 4624
    #
    # becomes
    #
    # 4621 - 4627
    # --------------------------------------------------------

    return (

        entry_low,

        entry_high
        + ENTRY_EXTENSION_PRICE
    )


# ============================================================
# EXECUTE SIGNAL
# ============================================================

async def execute_signal(
    signal
):

    direction = signal[
        "direction"
    ]

    entry_low = signal[
        "entry_low"
    ]

    entry_high = signal[
        "entry_high"
    ]

    # --------------------------------------------------------
    # CURRENT PRICE
    # --------------------------------------------------------

    bid, ask = (
        await get_current_price()
    )

    if direction == "SELL":

        execution_price = bid

    else:

        execution_price = ask

    # --------------------------------------------------------
    # EXTENDED RANGE
    # --------------------------------------------------------

    extended_low, extended_high = (
        calculate_extended_range(
            direction,
            entry_low,
            entry_high
        )
    )

    signal[
        "execution_price"
    ] = execution_price

    signal[
        "execution_range_low"
    ] = extended_low

    signal[
        "execution_range_high"
    ] = extended_high

    # --------------------------------------------------------
    # CHECK ORIGINAL RANGE
    # --------------------------------------------------------

    inside_original = (

        entry_low
        <= execution_price
        <= entry_high
    )

    # --------------------------------------------------------
    # CHECK EXTENDED RANGE
    # --------------------------------------------------------

    inside_extended = (

        extended_low
        <= execution_price
        <= extended_high
    )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    print(
        "VALID SIGNAL RECEIVED "
        "FOR DEMO EXECUTION"
    )

    print(
        "=" * 70
    )

    print(
        f"Channel:   {signal['channel']}"
    )

    print(
        f"Direction: {direction}"
    )

    print(
        f"Entry:     "
        f"{entry_low} - "
        f"{entry_high}"
    )

    print(
        f"SL:        "
        f"{signal['stoploss']}"
    )

    mapping_text = " + ".join(
        f"TP{x}"
        for x in signal[
            "execution_tp_numbers"
        ]
    )

    print(
        f"TP mapping: {mapping_text}"
    )

    for tp_number in signal[
        "execution_tp_numbers"
    ]:

        print(
            f"TP{tp_number}: "
            f"{signal['execution_tps'][tp_number]}"
        )

    print(
        "â± Signal age: 0.00 minutes"
    )

    print(
        f"ðŸ’° {SYMBOL} BID: "
        f"{bid:.3f}"
    )

    print(
        f"ðŸ’° {SYMBOL} ASK: "
        f"{ask:.3f}"
    )

    print()

    print(
        f"Original entry range: "
        f"{entry_low:.3f} - "
        f"{entry_high:.3f}"
    )

    print(
        f"30-pip extended range: "
        f"{extended_low:.3f} - "
        f"{extended_high:.3f}"
    )

    print(
        f"Execution price: "
        f"{execution_price:.3f}"
    )

    # --------------------------------------------------------
    # ORIGINAL RANGE
    # --------------------------------------------------------

    if inside_original:

        print(
            "Entry condition: "
            "âœ… INSIDE ORIGINAL RANGE"
        )

    # --------------------------------------------------------
    # EXTENDED RANGE
    # --------------------------------------------------------

    elif inside_extended:

        print(
            "Entry condition: "
            "ðŸŸ¡ OUTSIDE ORIGINAL RANGE"
        )

        print(
            "30-pip extension: "
            "âœ… ACCEPTED"
        )

        print()
        print(
            "ðŸŸ¡ 30-PIP ENTRY EXTENSION USED"
        )

        print(
            f"Original range: "
            f"{entry_low} - "
            f"{entry_high}"
        )

        print(
            f"Execution range: "
            f"{extended_low:.3f} - "
            f"{extended_high:.3f}"
        )

    # --------------------------------------------------------
    # OUTSIDE EVERYTHING
    # --------------------------------------------------------

    else:

        print(
            "Entry condition: "
            "âŒ OUTSIDE 30-PIP EXTENDED RANGE"
        )

        print(
            "â›” No trade placed."
        )

        return (
            False,
            []
        )

    # --------------------------------------------------------
    # EXECUTE TWO POSITIONS
    # --------------------------------------------------------

    positions = []

    selected_tps = signal[
        "execution_tp_numbers"
    ][:POSITIONS_PER_SIGNAL]

    for position_number, tp_number in enumerate(
        selected_tps,
        start=1
    ):

        tp_price = signal[
            "execution_tps"
        ][
            tp_number
        ]

        print()
        print(
            "-" * 70
        )

        print(
            f"ðŸš€ EXECUTING POSITION "
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
            f"SL:        "
            f"{signal['stoploss']}"
        )

        print(
            f"TP{tp_number}:      "
            f"{tp_price}"
        )

        try:

            # ------------------------------------------------
            # BUY
            # ------------------------------------------------

            if direction == "BUY":

                result = (
                    await connection
                    .create_market_buy_order(
                        SYMBOL,
                        LOT_SIZE,
                        signal[
                            "stoploss"
                        ],
                        tp_price
                    )
                )

            # ------------------------------------------------
            # SELL
            # ------------------------------------------------

            else:

                result = (
                    await connection
                    .create_market_sell_order(
                        SYMBOL,
                        LOT_SIZE,
                        signal[
                            "stoploss"
                        ],
                        tp_price
                    )
                )

            print()
            print(
                "ðŸ“¨ MetaApi result:"
            )

            print(
                result
            )

            result_code = get_field(
                result,
                "stringCode",
                ""
            )

            position_id = get_field(
                result,
                "positionId",
                None
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if result_code in (
                "TRADE_RETCODE_DONE",
                "TRADE_RETCODE_PLACED",
                ""
            ):

                print()
                print(
                    f"âœ… POSITION "
                    f"{position_number} "
                    f"EXECUTED SUCCESSFULLY"
                )

                if position_id:

                    print(
                        f"   Position ID: "
                        f"{position_id}"
                    )

                positions.append({

                    "position_number":
                        position_number,

                    "tp_number":
                        tp_number,

                    "tp":
                        tp_price,

                    "result_code":
                        result_code,

                    "position_id":
                        position_id,

                    "result":
                        str(result),
                })

            else:

                print()
                print(
                    f"âŒ POSITION "
                    f"{position_number} FAILED"
                )

                print(
                    f"MetaApi code: "
                    f"{result_code}"
                )

        except Exception as error:

            print()
            print(
                f"âŒ POSITION "
                f"{position_number} "
                f"EXECUTION ERROR:"
            )

            print(
                error
            )

    # --------------------------------------------------------
    # BOTH POSITIONS REQUIRED
    # --------------------------------------------------------

    if len(positions) == (
        POSITIONS_PER_SIGNAL
    ):

        return (
            True,
            positions
        )

    return (
        False,
        positions
    )


# ============================================================
# TELEGRAM NOTIFICATION
# ============================================================

async def send_notification(
    message
):

    if not TELEGRAM_BOT_TOKEN:

        return

    if not TELEGRAM_NOTIFICATION_CHAT_ID:

        return

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/"
        "sendMessage"
    )

    payload = {

        "chat_id":
            TELEGRAM_NOTIFICATION_CHAT_ID,

        "text":
            message,
    }

    try:

        async with aiohttp.ClientSession() as session:

            async with session.post(
                url,
                json=payload,
                timeout=15
            ) as response:

                if response.status != 200:

                    body = (
                        await response.text()
                    )

                    print(
                        "âš ï¸ Telegram "
                        "notification failed:"
                    )

                    print(
                        body
                    )

    except Exception as error:

        print(
            "âš ï¸ Telegram "
            f"notification failed: {error}"
        )


# ============================================================
# RESOLVE TELEGRAM SOURCES
# ============================================================

async def resolve_sources(
    client
):

    global resolved_sources

    print()
    print(
        "=" * 70
    )

    print(
        "RESOLVING TELEGRAM SOURCES"
    )

    print(
        "=" * 70
    )

    resolved_sources = []

    for source in SOURCE_CHANNELS:

        print()
        print(
            f"ðŸ” {source}"
        )

        try:

            entity = (
                await client.get_entity(
                    source
                )
            )

            chat_id = int(
                utils.get_peer_id(entity)
            )

            title = (

                getattr(
                    entity,
                    "title",
                    None
                )

                or getattr(
                    entity,
                    "username",
                    None
                )

                or str(source)
            )

            resolved_sources.append(
                entity
            )

            resolved_chat_ids.add(
                chat_id
            )

            source_names[
                chat_id
            ] = title

            print(
                "   âœ… ACCESSIBLE"
            )

            print(
                f"   Name: {title}"
            )

            print(
                f"   ID: {chat_id}"
            )

        except (
            UsernameInvalidError,
            UsernameNotOccupiedError,
            ValueError
        ) as error:

            print(
                f"   âŒ FAILED: {error}"
            )

        except Exception as error:

            print(
                f"   âŒ FAILED: {error}"
            )

    print()

    print(
        f"Accessible sources: "
        f"{len(resolved_sources)}/"
        f"{len(SOURCE_CHANNELS)}"
    )

    return resolved_sources


# ============================================================
# DISPLAY TP RULES
# ============================================================

def display_tp_rules():

    print()
    print(
        "=" * 70
    )

    print(
        "TP RULES"
    )

    print(
        "=" * 70
    )

    print(
        "  â€¢ GOLD SIGNAL VIP â†’ TP3 + TP6"
    )

    print(
        "  â€¢ GOLD HUNTER TRADE â†’ TP3 + TP4"
    )

    print(
        "  â€¢ GOLD SIGNALS 98% SURE â†’ TP3 + TP4"
    )

    print(
        "  â€¢ GOLD VIP SIGNALS INSIGHTS â†’ TP3 + TP6"
    )

    print(
        "  â€¢ GUNS THE TRADER â†’ dynamic"
    )

    print(
        "      4 TPs â†’ TP3 + TP4"
    )

    print(
        "      6 TPs â†’ TP3 + TP6"
    )

    print()
    print(
        "ENTRY EXTENSION RULE:"
    )

    print(
        "  â€¢ SELL â†’ lower boundary - 3.0"
    )

    print(
        "  â€¢ BUY â†’ upper boundary + 3.0"
    )


# ============================================================
# TELEGRAM MESSAGE HANDLER
# ============================================================
#
# IMPORTANT FOR RENDER:
#
# We do NOT rely on:
#
#     events.NewMessage(chats=resolved_sources)
#
# Instead we listen globally and manually filter using
# numeric Telegram chat IDs.
#
# This is more reliable for the cloud deployment.
#
# ============================================================

async def handle_message(
    event
):

    try:

        chat_id = int(
            event.chat_id
        )

        # ----------------------------------------------------
        # NUMERIC CHAT ID FILTER
        # ----------------------------------------------------

        if chat_id not in (
            resolved_chat_ids
        ):

            return

        message_text = (
            event.raw_text
            or ""
        )

        if not message_text.strip():

            return

        chat = (
            await event.get_chat()
        )

        channel_name = (

            getattr(
                chat,
                "title",
                None
            )

            or getattr(
                chat,
                "username",
                None
            )

            or source_names.get(
                chat_id,
                "Unknown"
            )
        )

        message_id = int(
            event.message.id
        )

        print()
        print(
            "=" * 70
        )

        print(
            "ðŸ“¨ NEW TELEGRAM MESSAGE"
        )

        print(
            "=" * 70
        )

        print(
            f"Channel: {channel_name}"
        )

        print(
            f"Chat ID: {chat_id}"
        )

        print(
            f"Message ID: {message_id}"
        )

        print()
        print(
            "RAW MESSAGE"
        )

        print(
            "-" * 70
        )

        print(
            message_text
        )

        print(
            "-" * 70
        )

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        signal = parse_signal(

            message_text,

            channel_name,

            chat_id,

            message_id
        )

        # ----------------------------------------------------
        # INVALID
        # ----------------------------------------------------

        if not signal[
            "parse_success"
        ]:

            print()

            print(
                "ðŸ”´ MESSAGE "
                "REJECTED BY PARSER"
            )

            for error in signal[
                "validation_errors"
            ]:

                print(
                    f"   âŒ {error}"
                )

            return

        # ----------------------------------------------------
        # VALID
        # ----------------------------------------------------

        print()

        print(
            "ðŸŸ¢ SIGNAL PARSED "
            "SUCCESSFULLY"
        )

        print(
            f"Direction: "
            f"{signal['direction']}"
        )

        print(
            f"Entry: "
            f"{signal['entry_low']} - "
            f"{signal['entry_high']}"
        )

        print(
            f"SL: "
            f"{signal['stoploss']}"
        )

        print(
            f"All TPs: "
            f"{signal['tp_levels']}"
        )

        # ----------------------------------------------------
        # DUPLICATE CHECK
        # ----------------------------------------------------

        signal_key = (
            f"{chat_id}:"
            f"{message_id}"
        )

        if signal_key in (
            executed_signals
        ):

            print()

            print(
                "âš ï¸ SIGNAL ALREADY "
                "EXECUTED"
            )

            print(
                f"Signal key: "
                f"{signal_key}"
            )

            return

        # ----------------------------------------------------
        # EXECUTE
        # ----------------------------------------------------

        success, positions = (
            await execute_signal(
                signal
            )
        )

        # ----------------------------------------------------
        # SUCCESSFUL EXECUTION
        # ----------------------------------------------------

        if success:

            save_executed_signal(
                signal_key,
                signal,
                positions
            )

            save_trade_log(
                signal,
                positions
            )

            await send_notification(

                "âœ… DEMO TRADE EXECUTED\n"

                f"Channel: "
                f"{signal['channel']}\n"

                f"Direction: "
                f"{signal['direction']}\n"

                f"Symbol: "
                f"{SYMBOL}\n"

                f"Entry: "
                f"{signal['entry_low']}-"
                f"{signal['entry_high']}\n"

                f"TPs: "
                f"{signal['execution_tps']}"
            )

            print()

            print(
                "=" * 70
            )

            print(
                "DEMO SIGNAL "
                "EXECUTION FINISHED"
            )

            print(
                "=" * 70
            )

        # ----------------------------------------------------
        # PARTIAL / FAILED
        # ----------------------------------------------------

        else:

            print()

            print(
                "âš ï¸ SIGNAL WAS NOT "
                "FULLY EXECUTED"
            )

            print(
                f"Successful positions: "
                f"{len(positions)}/"
                f"{POSITIONS_PER_SIGNAL}"
            )

            # Do NOT mark failed/partial signals as executed.
            # This makes it possible to retry if appropriate.

    except Exception as error:

        print()

        print(
            "âŒ ERROR PROCESSING "
            "TELEGRAM MESSAGE:"
        )

        print(
            error
        )

        import traceback

        traceback.print_exc()


# ============================================================
# MAIN
# ============================================================

async def main():

    global metaapi
    global account
    global connection

    print()
    print(
        "=" * 70
    )

    print(
        "PHASE 6 - DEMO TELEGRAM "
        "â†’ MT5 EXECUTOR"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "âš ï¸ DEMO-ONLY MODE"
    )

    print(
        "âš ï¸ NO LIVE ACCOUNT "
        "TRADING ALLOWED"
    )

    print()

    print(
        f"Symbol: {SYMBOL}"
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
        f"{ENTRY_EXTENSION_PRICE}"
    )

    # --------------------------------------------------------
    # TELEGRAM STRING SESSION
    # --------------------------------------------------------

    print()

    print(
        "ðŸ” Telegram authentication mode:"
    )

    if TELEGRAM_SESSION_STRING:

        print(
            "   StringSession"
        )

        print(
            "   âœ… TELEGRAM_SESSION_STRING found"
        )

    else:

        print(
            "   âŒ TELEGRAM_SESSION_STRING missing"
        )

        raise RuntimeError(
            "TELEGRAM_SESSION_STRING "
            "environment variable is required."
        )

    # --------------------------------------------------------
    # REQUIRED ENVIRONMENT VARIABLES
    # --------------------------------------------------------

    if not API_HASH:

        raise RuntimeError(
            "TELEGRAM_API_HASH "
            "is missing."
        )

    if not METAAPI_TOKEN:

        raise RuntimeError(
            "METAAPI_TOKEN "
            "is missing."
        )

    if not METAAPI_ACCOUNT_ID:

        raise RuntimeError(
            "METAAPI_ACCOUNT_ID "
            "is missing."
        )

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    load_execution_memory()

    # ========================================================
    # METAAPI
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "CONNECTING TO METAAPI"
    )

    print(
        "=" * 70
    )

    metaapi = MetaApi(
        METAAPI_TOKEN
    )

    print(
        "âœ… MetaApi SDK initialized"
    )

    account = (
        await metaapi
        .metatrader_account_api
        .get_account(
            METAAPI_ACCOUNT_ID
        )
    )

    account_name = get_field(
        account,
        "name",
        METAAPI_ACCOUNT_ID
    )

    account_server = get_field(
        account,
        "server",
        "Unknown"
    )

    account_state = get_field(
        account,
        "state",
        "Unknown"
    )

    print(
        f"âœ… Account found: "
        f"{account_name}"
    )

    print(
        f"   Server: "
        f"{account_server}"
    )

    print(
        f"   State: "
        f"{account_state}"
    )

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    server_text = str(
        account_server
    ).lower()

    if "demo" not in server_text:

        raise RuntimeError(

            "ðŸ›‘ SAFETY STOP: "
            "Configured MetaApi account "
            "does not appear to be a "
            "DEMO account."
        )

    print(
        "ðŸŸ¢ DEMO ACCOUNT CONFIRMED"
    )

    # --------------------------------------------------------
    # DEPLOY ACCOUNT IF NECESSARY
    # --------------------------------------------------------

    if str(
        account_state
    ).upper() != "DEPLOYED":

        print(
            "â³ Deploying MetaApi account..."
        )

        await account.deploy()

    # --------------------------------------------------------
    # WAIT FOR CONNECTION
    # --------------------------------------------------------

    print(
        "â³ Waiting for MT5 connection..."
    )

    await account.wait_connected()

    print(
        "âœ… MT5 ACCOUNT CONNECTED"
    )

    # --------------------------------------------------------
    # RPC CONNECTION
    # --------------------------------------------------------

    connection = (
        account.get_rpc_connection()
    )

    await connection.connect()

    print(
        "âœ… RPC connection established"
    )

    # --------------------------------------------------------
    # SYNCHRONIZATION
    # --------------------------------------------------------

    await connection.wait_synchronized()

    print(
        "âœ… MT5 ACCOUNT SYNCHRONIZED"
    )

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    await verify_symbol()

    # ========================================================
    # TELEGRAM
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "CONNECTING TO TELEGRAM"
    )

    print(
        "=" * 70
    )

    client = TelegramClient(

        StringSession(
            TELEGRAM_SESSION_STRING
        ),

        API_ID,

        API_HASH
    )

    await client.start()

    if not await client.is_user_authorized():

        raise RuntimeError(
            "Telegram StringSession "
            "is not authorized."
        )

    print(
        "âœ… TELEGRAM SESSION AUTHORIZED"
    )

    # --------------------------------------------------------
    # RESOLVE SOURCES
    # --------------------------------------------------------

    await resolve_sources(
        client
    )

    if not resolved_sources:

        raise RuntimeError(
            "No Telegram source "
            "channels are accessible."
        )

    # ========================================================
    # ACTIVE
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "PHASE 6 DEMO EXECUTOR ACTIVE"
    )

    print(
        "=" * 70
    )

    print()
    print(
        "MONITORING:"
    )

    # IMPORTANT:
    # Use a normal loop rather than nested f-strings.

    for chat_id in sorted(
        resolved_chat_ids
    ):

        display_name = (
            source_names.get(
                chat_id,
                "Unknown"
            )
        )

        print(
            f"  â€¢ {display_name}"
        )

    print()
    print(
        "TRADE SETTINGS:"
    )

    print(
        f"  â€¢ Symbol: {SYMBOL}"
    )

    print(
        "  â€¢ Position 1: "
        "source TP mapping"
    )

    print(
        "  â€¢ Position 2: "
        "source TP mapping"
    )

    print(
        f"  â€¢ Volume: "
        f"{LOT_SIZE} each"
    )

    print(
        "  â€¢ Same entry range"
    )

    print(
        "  â€¢ Same stop loss"
    )

    print(
        f"  â€¢ {ENTRY_EXTENSION_PIPS}-pip "
        "entry extension"
    )

    print(
        "  â€¢ DEMO ONLY"
    )

    display_tp_rules()

    # --------------------------------------------------------
    # IMPORTANT RENDER FIX
    # --------------------------------------------------------
    #
    # Listen globally.
    #
    # We manually check event.chat_id inside
    # handle_message().
    #
    # This avoids problems with Telegram entity
    # filtering on cloud deployments.
    #
    # --------------------------------------------------------

    client.add_event_handler(

        handle_message,

        events.NewMessage()
    )

    print()
    print(
        "=" * 70
    )

    print(
        "TELEGRAM LISTENER ACTIVE"
    )

    print(
        "=" * 70
    )

    print()
    print(
        "Waiting for Telegram signals..."
    )

    print(
        "Press CTRL+C to stop."
    )

    # --------------------------------------------------------
    # RUN FOREVER
    # --------------------------------------------------------

    try:

        await client.run_until_disconnected()

    finally:

        try:

            await client.disconnect()

        except Exception:

            pass

        print(
            "Telegram client disconnected."
        )


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
            "ðŸ›‘ Phase 6 stopped by user."
        )

    except Exception as error:

        print()

        print(
            "âŒ FATAL ERROR:"
        )

        print(
            error
        )

        import traceback

        traceback.print_exc()
