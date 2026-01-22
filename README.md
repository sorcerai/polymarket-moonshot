# Polymarket Moonshot Tracker

Turn $50 into $100k on Polymarket. This is gambling. You will probably lose everything.

## What is this?

A Python script that scans Polymarket for cheap longshot opportunities. It:

1. Finds contracts trading under 5 cents (20x+ potential payout)
2. Calculates an "edge score" based on volume, liquidity, and market efficiency
3. Builds a compound betting strategy to maximize moonshot potential
4. Recommends position sizing across multiple bets

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/polymarket-moonshot.git
cd polymarket-moonshot
pip install -r requirements.txt
```

## Usage

```bash
# Default: $50 starting capital, $100k target
python moonshot.py

# Custom starting capital
python moonshot.py --capital 100

# Custom target
python moonshot.py --target 50000

# Look at contracts up to 10 cents (10x+ potential)
python moonshot.py --max-price 0.10

# Only show markets with $50k+ volume
python moonshot.py --min-volume 50000
```

## Example Output

```
======================================================================
MOONSHOT TRACKER - $50 -> $100K CHALLENGE
======================================================================

COMPOUND STRATEGY
   Starting: $50.00
   Target: $100,000.00
   Required: 2,000x total
   Stages: 4
   Per stage: 6.7x

STAGE BREAKDOWN
   [>] Stage 1: $50.00 -> $335.00 (6.7x)
   [ ] Stage 2: $335.00 -> $2,241.00 (6.7x)
   [ ] Stage 3: $2,241.00 -> $14,994.00 (6.7x)
   [ ] Stage 4: $14,994.00 -> $100,321.00 (6.7x)

TOP OPPORTUNITIES (by edge score)
----------------------------------------------------------------------
 1. [YOLO] $0.0100 -> 100x
    Edge: 75/100 | Vol: $45,000 | 45d
    Will aliens make contact before 2026?
    https://polymarket.com/event/aliens-2026
```

## Strategy

The script breaks down your moonshot into stages:

- **$50 → $100k** requires a 2000x return
- That's nearly impossible in one bet
- But 4 stages of 6.7x each is more achievable
- Each stage, you bet on multiple longshots
- If ANY ONE hits, you move to the next stage

## Risk Tiers

| Tier | Multiplier | Description |
|------|------------|-------------|
| YOLO | 1000x+ | Mass extinction event odds |
| MOONSHOT | 100-1000x | Genuine longshot |
| LONGSHOT | 20-100x | Unlikely but possible |
| VALUE | 5-20x | Underpriced favorite upset |

## Edge Score

The script calculates an "edge score" (0-100) based on:

- **Volume**: Lower volume = less efficient pricing = potential edge
- **Liquidity**: Lower liquidity = harder to trade = potential mispricing
- **Category**: Obscure categories get less attention

Higher edge score = better opportunity.

## Disclaimer

This is gambling. Not financial advice. You will probably lose your money.

The script just finds cheap contracts - it has no idea if they'll actually win. Most won't. That's why they're cheap.

Only bet what you can afford to lose completely.

## License

MIT
