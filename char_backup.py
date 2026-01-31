import pandas as pd
import requests
from lightweight_charts import Chart
import time
import asyncio

# Global cache til at gemme data for de forskellige tidsrammer
cached_data = {}

# ---- HENT DATA FRA BINANCE ----
def fetch_binance_ohlcv(symbol="BTCUSDT", interval="1d", days=365):
    url = "https://api.binance.com/api/v3/klines"
    limit = 1000  # MAX fra Binance
    start_time = int((pd.Timestamp.now() - pd.Timedelta(days=days)).timestamp() * 1000)
    all_data = []

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "startTime": start_time
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        # Stop hvis ingen data
        if not isinstance(data, list) or len(data) == 0:
            break

        all_data.extend(data)

        # Næste starttid
        last_open_time = data[-1][0]
        start_time = last_open_time + 1

        time.sleep(0.25)  # undgå rate limits

    # Konverter til DataFrame
    df = pd.DataFrame(all_data, columns=[
        "time","open","high","low","close","volume",
        "close_time","quote_volume","trades",
        "taker_base","taker_quote","ignore"
    ])

    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)

    return df[["time","open","high","low","close","volume"]]


# ---- HENT DATA FOR ANDRE TIDSRAMMER ----
def get_bar_data(symbol, timeframe):
    interval_mapping = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d',
    }

    if timeframe not in interval_mapping:
        raise ValueError(f"Ugyldig tidsramme: {timeframe}")

    max_days_mapping = {
        '1d': 3650,
        '5m': 30,
        '15m': 60,
        '1h': 500,
        '1m': 5,
        '30m': 30,
        '4h': 800,
    }

    days = max_days_mapping.get(timeframe, 7)

    if timeframe in cached_data:
        return cached_data[timeframe]

    data = fetch_binance_ohlcv(symbol, interval_mapping[timeframe], days=days)
    cached_data[timeframe] = data
    return data


# ---- OPDATERING AF CHART ----
async def on_timeframe_selection(chart, selected_timeframe='1d', symbol='BTCUSDT'):
    new_data = get_bar_data(symbol, selected_timeframe)
    chart.set(new_data, True)


# ---- MAIN PROGRAM ----
async def main():
    symbol = 'BTCUSDT'
    chart = Chart()

    initial_data = fetch_binance_ohlcv(symbol, "1d", days=3650)
    chart.set(initial_data)

    await on_timeframe_selection(chart, '1d', symbol)

    def switcher_func(chart_obj):
        selected = chart_obj.topbar['timeframe'].value
        asyncio.create_task(on_timeframe_selection(chart_obj, selected, symbol))

    chart.topbar.switcher(
        'timeframe',
        ('1m', '5m', '15m', '30m', '1h', '4h', '1d'),
        default='1d',
        func=switcher_func
    )

    await chart.show_async()


if __name__ == '__main__':
    asyncio.run(main())
