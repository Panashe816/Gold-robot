import asyncio
import os

from dotenv import load_dotenv
from metaapi_cloud_sdk import MetaApi


load_dotenv()

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")

# ============================================================
# WELTRADE GOLD SYMBOL
# ============================================================

SYMBOL = "XAUUSD_i"


async def main():

    print("=" * 70)
    print("PHASE 5 - METAAPI MT5 CONNECTION TEST")
    print("=" * 70)

    if not METAAPI_TOKEN:
        print("❌ METAAPI_TOKEN missing from .env")
        return

    if not METAAPI_ACCOUNT_ID:
        print("❌ METAAPI_ACCOUNT_ID missing from .env")
        return

    print("✅ MetaApi token loaded")
    print("✅ MetaApi account ID loaded")
    print()

    api = None
    connection = None

    try:

        # --------------------------------------------------
        # CONNECT TO METAAPI
        # --------------------------------------------------

        print("🔌 Connecting to MetaApi...")

        api = MetaApi(METAAPI_TOKEN)

        print("✅ MetaApi SDK initialized")
        print()

        # --------------------------------------------------
        # GET ACCOUNT
        # --------------------------------------------------

        print("🔍 Loading MT5 account...")

        account = await api.metatrader_account_api.get_account(
            METAAPI_ACCOUNT_ID
        )

        print("✅ MT5 account found")
        print()

        print("ACCOUNT INFORMATION")
        print("-" * 70)
        print(f"Name:       {account.name}")
        print(f"ID:         {account.id}")
        print(f"State:      {account.state}")
        print(f"Server:     {account.server}")
        print(f"Login:      {account.login}")
        print()

        # --------------------------------------------------
        # DEPLOY IF NECESSARY
        # --------------------------------------------------

        if account.state != "DEPLOYED":

            print("🔄 Account is not deployed.")
            print("🔄 Deploying MetaApi account...")

            await account.deploy()

            print("✅ Deployment requested")

        else:

            print("✅ Account already deployed")

        print()

        # --------------------------------------------------
        # WAIT FOR CONNECTION
        # --------------------------------------------------

        print("⏳ Waiting for MT5 connection...")

        await account.wait_connected()

        print("✅ MT5 ACCOUNT CONNECTED")
        print()

        # --------------------------------------------------
        # RPC CONNECTION
        # --------------------------------------------------

        print("🔌 Creating RPC connection...")

        connection = account.get_rpc_connection()

        await connection.connect()

        print("✅ RPC connection established")
        print()

        print("⏳ Waiting for synchronization...")

        await connection.wait_synchronized()

        print("✅ MT5 ACCOUNT SYNCHRONIZED")
        print()

        # --------------------------------------------------
        # ACCOUNT INFORMATION
        # --------------------------------------------------

        print("=" * 70)
        print("MT5 ACCOUNT INFORMATION")
        print("=" * 70)

        account_info = await connection.get_account_information()

        print(f"Balance:     {account_info.get('balance')}")
        print(f"Equity:      {account_info.get('equity')}")
        print(f"Currency:    {account_info.get('currency')}")
        print(f"Leverage:    {account_info.get('leverage')}")
        print(f"Broker:      {account_info.get('broker')}")
        print()

        # --------------------------------------------------
        # GOLD SYMBOL SPECIFICATION
        # --------------------------------------------------

        print("=" * 70)
        print(f"{SYMBOL} SYMBOL TEST")
        print("=" * 70)

        try:

            symbol_spec = await connection.get_symbol_specification(
                SYMBOL
            )

            if symbol_spec:

                print(f"✅ {SYMBOL} FOUND")
                print()

                print(f"Symbol:          {symbol_spec.get('symbol')}")
                print(f"Digits:          {symbol_spec.get('digits')}")
                print(f"Point:           {symbol_spec.get('point')}")
                print(f"Min volume:      {symbol_spec.get('minVolume')}")
                print(f"Max volume:      {symbol_spec.get('maxVolume')}")
                print(f"Volume step:     {symbol_spec.get('volumeStep')}")
                print()

            else:

                print(
                    f"⚠️ {SYMBOL} specification returned empty"
                )

        except Exception as e:

            print(
                f"⚠️ {SYMBOL} specification error: {e}"
            )

        # --------------------------------------------------
        # LIVE GOLD PRICE TEST
        # --------------------------------------------------

        print("=" * 70)
        print(f"LIVE {SYMBOL} PRICE TEST")
        print("=" * 70)

        try:

            price = await connection.get_symbol_price(
                SYMBOL
            )

            if price:

                print(
                    f"✅ LIVE {SYMBOL} PRICE RECEIVED"
                )
                print()

                print(f"Bid:         {price.get('bid')}")
                print(f"Ask:         {price.get('ask')}")
                print(f"Time:        {price.get('time')}")

            else:

                print(
                    f"⚠️ No {SYMBOL} price returned"
                )

        except Exception as e:

            print(
                f"⚠️ Price request failed: {e}"
            )

        # --------------------------------------------------
        # POSITIONS TEST
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("OPEN POSITIONS TEST")
        print("=" * 70)

        try:

            positions = await connection.get_positions()

            print(
                f"✅ Open positions retrieved: {len(positions)}"
            )

            for position in positions:

                print(
                    f"   {position.get('symbol')} "
                    f"{position.get('type')} "
                    f"volume={position.get('volume')}"
                )

        except Exception as e:

            print(
                f"⚠️ Position request failed: {e}"
            )

        # --------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("PHASE 5 CONNECTION TEST RESULT")
        print("=" * 70)

        print("✅ MetaApi authentication: PASS")
        print("✅ MT5 account lookup:     PASS")
        print("✅ MT5 connection:         PASS")
        print("✅ RPC synchronization:    PASS")
        print("✅ Account information:    PASS")
        print(f"✅ {SYMBOL} test:            CHECK ABOVE")
        print("✅ Position access:         CHECK ABOVE")

        print()
        print("⚠️ NO TRADES WERE PLACED")
        print("⚠️ THIS IS A CONNECTION-ONLY TEST")
        print("=" * 70)

        # Keep connection alive briefly
        await asyncio.sleep(3)

        if connection:
            await connection.close()

    except Exception as e:

        print()
        print("=" * 70)
        print("❌ PHASE 5 CONNECTION TEST FAILED")
        print("=" * 70)
        print()
        print(f"ERROR: {e}")
        print()

    finally:

        if api:

            try:
                await api.close()
            except Exception:
                pass


if __name__ == "__main__":

    asyncio.run(main())