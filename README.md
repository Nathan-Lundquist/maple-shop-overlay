# Maple Shop Checker

Always-on-top overlay for MapleStory Classic. Screen-reads open shop windows and
compares prices against NPC buy/sell prices from maplestory.io.

## Deal ratings

| Label   | Meaning                                                   |
|---------|-----------------------------------------------------------|
| FLIP $$ | Below NPC sell price — buy here, sell to NPC for profit   |
| GREAT   | Less than 60% of NPC buy price                            |
| GOOD    | 60–90% of NPC buy price                                   |
| FAIR    | ~NPC price (90–110%)                                      |
| NOPE    | More expensive than NPC — just buy from NPC instead       |
| ?       | Item not found in database                                |

## Setup

### Requirements

- Python 3.11+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and on PATH
- Windows (for the game window auto-detection; capture works on Linux/Mac too)

### Install

```bash
pip install -r requirements.txt
```

### 1. Populate the item database

Downloads item prices from maplestory.io (~30–60 min depending on item count):

```bash
python sync_db.py
```

Options:
```
--region GMS        Game region (GMS, KMS, JMS, TMS, SEA)
--version 64        Game version/patch number
--categories Use Etc Equip   Which item categories to sync
--delay 0.05        Seconds between API requests (lower = faster but more likely to rate-limit)
```

Re-run periodically to keep prices current (e.g. after game patches).

### 2. Run the overlay

```bash
python main.py
```

Open any NPC shop or player shop in-game. The overlay will automatically
detect the shop window and show deal ratings.

Options:
```
--interval 1.0      Seconds between screen scans (default 1.0)
```

## Debugging / Tuning

If no shop is detected, run the debug tool:

```bash
python debug_capture.py
```

To look up an item manually:

```bash
python debug_capture.py --lookup "White Potion"
```

To save an annotated screenshot of the detected shop area:

```bash
python debug_capture.py --save
```

## Tuning shop detection

If the shop window isn't being detected, the border color may not match the
default HSV range. Open `src/shop_reader.py` and adjust:

```python
BORDER_HUE_LO = np.array([15,  60,  100], dtype=np.uint8)
BORDER_HUE_HI = np.array([35, 200,  220], dtype=np.uint8)
```

Use `debug_capture.py --save` to capture the shop area, then check the HSV
values of the border with any image editor.

## Architecture

```
main.py                   Entry point, wires everything together
sync_db.py                One-time DB sync from maplestory.io
debug_capture.py          Debug/tuning helper

src/
  capture.py              Screen capture (mss)
  shop_reader.py          Shop window detection + row parsing
  ocr.py                  Tesseract OCR wrappers
  matcher.py              Fuzzy name matching (OCR text → DB item)
  deal.py                 Deal rating logic
  database.py             SQLite DB (items + sync log)
  api_client.py           maplestory.io API client
  overlay.py              tkinter always-on-top overlay
  platforms/
    windows.py            Win32 game window finding
```

## NPC price notes

- `npc_buy_price` — what an NPC charges you to buy the item
- `npc_sell_price` — what an NPC pays you for the item (~20% of buy price)
- Source: `metaInfo.price` from the maplestory.io item API
- Items with `price = 0` cannot be sold to NPCs (flagged as UNKNOWN)
