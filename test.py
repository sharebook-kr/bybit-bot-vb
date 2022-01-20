from pybit import HTTP
import pprint

with open("./bybit.key") as f:
    lines = f.readlines()
    api_key = lines[0].strip()
    api_secret = lines[1].strip()

session = HTTP(
    endpoint="https://api.bybit.com", 
    api_key=api_key, 
    api_secret=api_secret,
    spot=False
)

resp = session.place_active_order(
    symbol="XRPUSDT",
    side="Buy",
    order_type="Market",
    qty=46,
    time_in_force="GoodTillCancel",
    reduce_only=True,
    close_on_trigger=False
)

pprint.pprint(resp)