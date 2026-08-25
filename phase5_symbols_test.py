import os
import asyncio
from dotenv import load_dotenv
from metaapi_cloud_sdk import MetaApi

load_dotenv()

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")


async def main():

    print("=" * 70)
    print("PHASE 5 - MT5 SYMBOL DISCOVERY")
    print("=" * 70)

    if not METAAPI_TOKEN:
        print("❌ METAAPI_TOKEN missing from .env")
        return

    if not METAAPI_ACCOUNT_ID:
        print("❌ METAAPI_ACCOUNT_ID missing from .env")
        return

    print("✅ MetaApi token loaded")
    print("✅ MetaApi account ID loaded")

    api = None

    try:
        print("\n🔌 Connecting to MetaApi...")

        api = MetaApi(token=METAAPI_TOKEN)

        account = await api.metatrader_account_api.get_account(
            METAAPI_ACCOUNT_ID
        )

        print("✅ MT5 account found")
        print(f"State: {account.state}")

        if account.state != "DEPLOYED":
            print("❌ Account is not deployed.")
            return

        print("\n⏳ Waiting for MT5 connection...")
        await account.wait_connected()

        print("✅ MT5 ACCOUNT CONNECTED")

        connection = account.get_rpc_connection()

        print("\n🔌 Connecting RPC...")
        await connection.connect()

        print("✅ RPC connection established")

        print("\n⏳ Waiting for synchronization...")
        await connection.wait_synchronized()

        print("✅ MT5 ACCOUNT SYNCHRONIZED")

        print("\n" + "=" * 70)
        print("SEARCHING AVAILABLE SYMBOLS")
        print("=" * 70)

        # Get all symbols available on the MT5 account
        symbols = await connection.get_symbols()

        print(f"\nTotal symbols returned: {len(symbols)}")

        # Search specifically for gold-related symbols
        gold_symbols = []

        for symbol in symbols:
            symbol_upper = str(symbol).upper()

            if (
                "XAU" in symbol_upper
                or "GOLD" in symbol_upper
            ):
                gold_symbols.append(symbol)

        print("\n" + "=" * 70)
        print("GOLD-RELATED SYMBOLS")
        print("=" * 70)

        if gold_symbols:

            print(f"\n✅ Found {len(gold_symbols)} possible gold symbols:\n")

            for symbol in gold_symbols:
                print(f"   • {symbol}")

        else:

            print("\n❌ No symbols containing XAU or GOLD were found.")

            print("\nFirst 100 available symbols:")

            for symbol in symbols[:100]:
                print(f"   • {symbol}")

        print("\n" + "=" * 70)
        print("PHASE 5 SYMBOL DISCOVERY FINISHED")
        print("=" * 70)

    except Exception as e:

        print("\n" + "=" * 70)
        print("❌ SYMBOL DISCOVERY FAILED")
        print("=" * 70)

        print(f"\nERROR: {e}")

    finally:

        if api:
            try:
                await api.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())