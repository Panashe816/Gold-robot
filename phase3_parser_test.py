import re
from datetime import datetime
import pytz


# ============================================================
# PHASE 3 - GOLD SIGNAL PARSER TEST
# ============================================================
#
# PURPOSE:
#   Test whether our parser can correctly understand the
#   different signal formats received from our source channels.
#
# IMPORTANT:
#   This file DOES NOT:
#       - connect to Telegram
#       - connect to MetaApi
#       - connect to MT5
#       - place trades
#       - send messages
#
#   It is ONLY a parser test.
# ============================================================


TIMEZONE = pytz.timezone("Africa/Harare")


# ============================================================
# CHANNEL NAMES
# ============================================================

CHANNEL_GOLD_VIP = "GOLD VIP SIGNALS Insights"
CHANNEL_GOLD_SIGNAL_VIP = "GOLD SIGNAL VIP"
CHANNEL_GOLD_98 = "Gold Signals 98% Sure 😎"
CHANNEL_GOLD_HUNTER = "GOLD HUNTER TRADE"


# ============================================================
# HELPER: NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    """
    Normalize whitespace while preserving the actual words
    and numbers in the signal.
    """

    text = text.replace("\r", "\n")

    # Replace non-breaking spaces
    text = text.replace("\u00A0", " ")

    # Normalize repeated spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


# ============================================================
# EXTRACT DIRECTION
# ============================================================

def extract_direction(text):

    text_upper = text.upper()

    # Look for BUY before SELL
    if re.search(r"\bBUY\b", text_upper):
        return "BUY"

    if re.search(r"\bSELL\b", text_upper):
        return "SELL"

    return None


# ============================================================
# EXTRACT ENTRY
# ============================================================

def extract_entry(text):

    # --------------------------------------------------------
    # Entry ranges
    #
    # Supports:
    #   4547/4544
    #   4547 / 4544
    #   4545_4542
    #   4545 _ 4542
    #   4500-4510
    #   4500 - 4510
    # --------------------------------------------------------

    range_patterns = [

        r"\b(\d+(?:\.\d+)?)\s*[/_]\s*(\d+(?:\.\d+)?)\b",

        r"\b(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\b"
    ]

    for pattern in range_patterns:

        match = re.search(pattern, text)

        if match:

            a = float(match.group(1))
            b = float(match.group(2))

            return min(a, b), max(a, b), "RANGE"

    # --------------------------------------------------------
    # Single entry
    #
    # Look specifically near GOLD / XAUUSD / BUY / SELL
    # so that TP and SL values aren't accidentally selected.
    # --------------------------------------------------------

    single_patterns = [

        # GOLD BUY 4350
        r"\b(?:GOLD|XAUUSD|XAU)\b\s+(?:BUY|SELL)\b(?:\s+NOW)?\s+(\d+(?:\.\d+)?)(?:\s+00\b)?",

        # BUY GOLD 4350
        r"\b(?:BUY|SELL)\b\s+(?:GOLD|XAUUSD|XAU)\b(?:\s+NOW)?\s+(\d+(?:\.\d+)?)(?:\s+00\b)?",

        # GOLD BUY NOW 4545
        r"\bGOLD\b\s+(?:BUY|SELL)\b\s+NOW\s+(\d+(?:\.\d+)?)"
    ]

    for pattern in single_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = float(match.group(1))

            return value, value, "SINGLE"

    return None, None, None


# ============================================================
# EXTRACT STOP LOSS
# ============================================================

def extract_sl(text):

    patterns = [

        # SL 4534
        r"\bSL\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)",

        # STOPLOSS 4534
        r"\bSTOPLOSS\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)",

        # STOP LOSS 4534
        r"\bSTOP\s+LOSS\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)",

        # STOP 4534
        r"\bSTOP\b\s*[:.\-]?\s*(\d+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return float(match.group(1))

    return None


# ============================================================
# EXTRACT TAKE PROFIT LEVELS
# ============================================================

def extract_tp_levels(text):

    tp_levels = {}

    patterns = [

        # TP1 4551
        # TP1. 4551
        # TP1: 4551
        # TP1 - 4551
        # TP1 = 4551
        r"\bTP\s*([1-9])\s*[:.\-=]?\s*(\d+(?:\.\d+)?)"
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for tp_number, tp_price in matches:

            tp_number = int(tp_number)
            tp_price = float(tp_price)

            tp_levels[tp_number] = tp_price

    return dict(sorted(tp_levels.items()))


# ============================================================
# VALIDATE PRICE RELATIONSHIPS
# ============================================================

def validate_price_relationships(
    direction,
    entry_low,
    entry_high,
    stoploss,
    tp_levels
):

    errors = []

    if direction not in ("BUY", "SELL"):

        errors.append("Missing BUY/SELL direction")

        return False, errors

    if entry_low is None:

        errors.append("Missing entry")

    if stoploss is None:

        errors.append("Missing stop loss")

    if entry_low is None or stoploss is None:

        return False, errors

    # --------------------------------------------------------
    # BUY
    #
    # Normal structure:
    #
    # SL < ENTRY < TP
    # --------------------------------------------------------

    if direction == "BUY":

        if stoploss >= entry_low:

            errors.append(
                f"BUY stop loss {stoploss} is not below "
                f"entry {entry_low}"
            )

        if tp_levels:

            first_tp = min(tp_levels.values())

            if first_tp <= entry_high:

                errors.append(
                    f"BUY TP1/first TP {first_tp} is not above "
                    f"entry high {entry_high}"
                )

    # --------------------------------------------------------
    # SELL
    #
    # Normal structure:
    #
    # TP < ENTRY < SL
    # --------------------------------------------------------

    elif direction == "SELL":

        if stoploss <= entry_high:

            errors.append(
                f"SELL stop loss {stoploss} is not above "
                f"entry {entry_high}"
            )

        if tp_levels:

            first_tp = max(tp_levels.values())

            if first_tp >= entry_low:

                errors.append(
                    f"SELL first TP {first_tp} is not below "
                    f"entry low {entry_low}"
                )

    # --------------------------------------------------------
    # Validate gold price range
    # --------------------------------------------------------

    all_prices = []

    if entry_low is not None:
        all_prices.append(entry_low)

    if entry_high is not None:
        all_prices.append(entry_high)

    if stoploss is not None:
        all_prices.append(stoploss)

    all_prices.extend(tp_levels.values())

    for price in all_prices:

        if not (1800 <= price <= 6000):

            errors.append(
                f"Price {price} is outside expected "
                f"Gold price range"
            )

    # --------------------------------------------------------
    # Maximum entry range
    # --------------------------------------------------------

    if entry_low is not None and entry_high is not None:

        if entry_high - entry_low > 100:

            errors.append(
                f"Entry range too wide: "
                f"{entry_low}-{entry_high}"
            )

    return len(errors) == 0, errors


# ============================================================
# PARSE SIGNAL
# ============================================================

def parse_signal(message, channel_name):

    message = normalize_text(message)

    direction = extract_direction(message)

    entry_low, entry_high, entry_type = extract_entry(message)

    stoploss = extract_sl(message)

    tp_levels = extract_tp_levels(message)

    validation_ok, validation_errors = (
        validate_price_relationships(
            direction,
            entry_low,
            entry_high,
            stoploss,
            tp_levels
        )
    )

    signal = {

        "channel": channel_name,

        "direction": direction,

        "entry": entry_low,

        "entry_low": entry_low,

        "entry_high": entry_high,

        "entry_type": entry_type,

        "stoploss": stoploss,

        "tp1": tp_levels.get(1),

        "tp2": tp_levels.get(2),

        "tp3": tp_levels.get(3),

        "tp4": tp_levels.get(4),

        "tp5": tp_levels.get(5),

        "tp6": tp_levels.get(6),

        "tp_levels": tp_levels,

        "parse_success": validation_ok,

        "validation_errors": validation_errors,

        "timestamp": datetime.now(TIMEZONE)
    }

    return signal


# ============================================================
# PRINT RESULT
# ============================================================

def print_signal_result(number, signal):

    print()
    print("=" * 70)
    print(f"SIGNAL {number} PARSER RESULT")
    print("=" * 70)

    print(f"Channel:       {signal['channel']}")
    print(f"Direction:     {signal['direction']}")

    print(
        f"Entry:         {signal['entry_low']} "
        f"to {signal['entry_high']}"
    )

    print(f"Entry type:    {signal['entry_type']}")

    print(f"Stop Loss:     {signal['stoploss']}")

    print(f"TP1:           {signal['tp1']}")
    print(f"TP2:           {signal['tp2']}")
    print(f"TP3:           {signal['tp3']}")
    print(f"TP4:           {signal['tp4']}")
    print(f"TP5:           {signal['tp5']}")
    print(f"TP6:           {signal['tp6']}")

    print()
    print(f"All TP levels: {signal['tp_levels']}")

    print()

    if signal["parse_success"]:

        print("STATUS:         ✅ VALID SIGNAL")

    else:

        print("STATUS:         ❌ INVALID SIGNAL")

        print("REASONS:")

        for error in signal["validation_errors"]:

            print(f"  - {error}")


# ============================================================
# TEST SIGNALS
# ============================================================

TEST_SIGNALS = [

    # --------------------------------------------------------
    # SIGNAL 1
    # GOLD VIP SIGNALS Insights - SELL
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_VIP,

        """
        🟥 GOLD SELL 4600 00

        🎯 TP1 4595 00
        🎯 TP2 4590 00
        🎯 TP3 4585 00
        🎯 TP4 4580 00
        🎯 TP5 4575 00
        🎯 TP6 4570 00

        🚫 SL. 4610.00
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 2
    # GOLD VIP SIGNALS Insights - BUY
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_VIP,

        """
        ‼️ GOLD BUY 4350 00

        🎯 TP1 4355 00
        🎯 TP2 4360 00
        🎯 TP3 4365 00
        🎯 TP4 4370 00
        🎯 TP5 4375 00
        🎯 TP6 4380 00

        🚫 SL. 4340.00 ❗
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 3
    # GOLD SIGNAL VIP - SELL
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_SIGNAL_VIP,

        """
        GOLD SELL 4588

        TP1 4584
        TP2 4580
        TP3 4576
        TP4 4572
        TP5 4566
        TP6 4562

        SL 4600
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 4
    # GOLD SIGNAL VIP - BUY
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_SIGNAL_VIP,

        """
        GOLD BUY 4349

        TP1 4353
        TP2 4357
        TP3 4361
        TP4 4365
        TP5 4369
        TP6 4372

        SL 4337
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 5
    # Gold Signals 98% Sure - BUY
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_98,

        """
        Forwarded from VIP Gold Signals 98% Sure (vip)

        شراء الذهب

        XAUUSD BUY 4547/4544

        TP1. 4551
        TP2. 4554
        TP3. 4558
        TP4. 4577

        SL. 4534

        استخدام إدارة الأموال

        Use Money Management
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 6
    # Gold Signals 98% Sure - SELL
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_98,

        """
        Forwarded from VIP Gold Signals 98% Sure (vip)

        بيع الذهب

        XAUUSD Sell 4353/4356

        TP1. 4349
        TP2. 4346
        TP3. 4342
        TP4. 4323

        SL. 4366

        استخدام إدارة الأموال

        Use Money Management
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 7
    # GOLD HUNTER TRADE - BUY
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_HUNTER,

        """
        GOLD BUY NOW 4545_4542

        TP1 4548
        TP2 4551
        TP3 4555
        TP4 4566

        SL : 4532
        """
    ),

    # --------------------------------------------------------
    # SIGNAL 8
    # GOLD HUNTER TRADE - SELL
    # --------------------------------------------------------

    (
        CHANNEL_GOLD_HUNTER,

        """
        GOLD Sell NOW 4494_4497

        TP1 4491
        TP2 4488
        TP3 4484
        TP4 4474

        SL : 4507
        """
    )
]


# ============================================================
# RUN ALL TESTS
# ============================================================

def main():

    print()
    print("=" * 70)
    print("PHASE 3 - GOLD SIGNAL PARSER TEST")
    print("=" * 70)

    print()
    print("Testing 8 real signal examples.")
    print()
    print("NO TELEGRAM CONNECTION")
    print("NO METAAPI CONNECTION")
    print("NO MT5 CONNECTION")
    print("NO TRADES")
    print()

    valid_count = 0
    invalid_count = 0

    for number, (channel, message) in enumerate(
        TEST_SIGNALS,
        start=1
    ):

        signal = parse_signal(
            message,
            channel
        )

        print_signal_result(
            number,
            signal
        )

        if signal["parse_success"]:

            valid_count += 1

        else:

            invalid_count += 1

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("PARSER TEST SUMMARY")
    print("=" * 70)

    print(f"Total signals tested:  {len(TEST_SIGNALS)}")
    print(f"Valid signals:         {valid_count}")
    print(f"Invalid signals:       {invalid_count}")

    print()

    if invalid_count == 0:

        print(
            "🎉 ALL 8 SIGNALS PASSED PARSER VALIDATION"
        )

    else:

        print(
            "⚠️ SOME SIGNALS FAILED VALIDATION"
        )

    print()
    print("=" * 70)
    print("PHASE 3 TEST FINISHED")
    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()