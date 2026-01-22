#!/usr/bin/env python3
"""
MOONSHOT TRACKER - Turn $50 into $100k

The degen's guide to Polymarket lottery tickets.
This is gambling. You will probably lose everything.
But someone did it, so why not try?

Strategy:
1. Find underpriced longshots (market inefficiencies)
2. Diversify across uncorrelated events
3. Compound winners into new positions
4. Track everything obsessively

Usage:
    python moonshot.py                    # Default: $50 -> $100k
    python moonshot.py --capital 100      # Start with $100
    python moonshot.py --target 50000     # Target $50k
    python moonshot.py --max-price 0.10   # Look at up to 10 cent contracts
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx

# Polymarket API endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


class RiskTier(Enum):
    YOLO = "YOLO"  # 1000x+ potential, mass extinction event odds
    MOONSHOT = "MOONSHOT"  # 100-1000x, genuine longshot
    LONGSHOT = "LONGSHOT"  # 20-100x, unlikely but possible
    VALUE = "VALUE"  # 5-20x, underpriced favorite upset


@dataclass
class MoonshotOpportunity:
    market_id: str
    question: str
    slug: str
    side: str
    price: float
    potential_multiplier: float
    volume: float
    liquidity: float
    days_to_expiry: float
    end_date: datetime
    risk_tier: RiskTier
    edge_score: float
    category: Optional[str] = None
    reasoning: str = ""


@dataclass
class CompoundStrategy:
    starting_capital: float
    target: float
    required_multiplier: float
    recommended_stages: int
    per_stage_multiplier: float
    current_stage: int = 1
    current_capital: float = 0
    positions: list = field(default_factory=list)


class PolymarketClient:
    """Async client for Polymarket's public APIs."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_markets(
        self,
        limit: int = 500,
        active: bool = True,
        closed: bool = False,
    ) -> list[dict]:
        """Fetch markets from Gamma API."""
        params = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": "volume",
            "ascending": "false",
        }

        try:
            resp = await self.client.get(f"{GAMMA_API}/markets", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            print(f"Error fetching markets: {e}")
            return []

    async def get_events(self, limit: int = 200) -> list[dict]:
        """Fetch events from Gamma API."""
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
        }

        try:
            resp = await self.client.get(f"{GAMMA_API}/events", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            print(f"Error fetching events: {e}")
            return []


class MoonshotTracker:
    """Find moonshot opportunities on Polymarket."""

    # Edge detection weights
    VOLUME_WEIGHT = 0.3
    RECENCY_WEIGHT = 0.2
    CATEGORY_WEIGHT = 0.2
    LIQUIDITY_WEIGHT = 0.3

    def __init__(self, client: PolymarketClient):
        self.client = client

    async def find_moonshots(
        self,
        max_price: float = 0.05,
        min_volume: float = 10000,
        min_days: float = 1,
        max_results: int = 50,
    ) -> list[MoonshotOpportunity]:
        """Find cheap longshot opportunities."""
        markets = await self.client.get_markets(limit=500)
        opportunities = []

        now = datetime.now(timezone.utc)

        for market in markets:
            try:
                # Parse market data
                end_date_str = market.get("endDate") or market.get("end_date_iso")
                if not end_date_str:
                    continue

                # Handle various date formats
                if end_date_str.endswith("Z"):
                    end_date = datetime.fromisoformat(
                        end_date_str.replace("Z", "+00:00")
                    )
                else:
                    end_date = datetime.fromisoformat(end_date_str)

                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)

                days_left = (end_date - now).total_seconds() / 86400

                if days_left < min_days:
                    continue

                # Get prices
                outcome_prices = market.get("outcomePrices")
                if not outcome_prices:
                    continue

                if isinstance(outcome_prices, str):
                    import json

                    outcome_prices = json.loads(outcome_prices)

                if not outcome_prices or len(outcome_prices) < 2:
                    continue

                yes_price = float(outcome_prices[0]) if outcome_prices[0] else 1.0
                no_price = float(outcome_prices[1]) if outcome_prices[1] else 1.0

                # Find the cheap side
                if yes_price <= no_price:
                    cheap_side = "YES"
                    price = yes_price
                else:
                    cheap_side = "NO"
                    price = no_price

                if price <= 0 or price > max_price:
                    continue

                volume = float(market.get("volume") or market.get("volumeNum") or 0)
                if volume < min_volume:
                    continue

                liquidity = float(
                    market.get("liquidity") or market.get("liquidityNum") or 0
                )

                # Calculate opportunity metrics
                multiplier = 1.0 / price
                edge_score = self._calculate_edge_score(market, volume, liquidity)
                risk_tier = self._classify_risk(multiplier)

                opp = MoonshotOpportunity(
                    market_id=market.get("id") or market.get("conditionId") or "",
                    question=market.get("question") or "",
                    slug=market.get("slug") or market.get("market_slug") or "",
                    side=cheap_side,
                    price=price,
                    potential_multiplier=multiplier,
                    volume=volume,
                    liquidity=liquidity,
                    days_to_expiry=days_left,
                    end_date=end_date,
                    risk_tier=risk_tier,
                    edge_score=edge_score,
                    category=market.get("groupItemTitle") or market.get("category"),
                    reasoning=self._generate_reasoning(market, edge_score, volume),
                )
                opportunities.append(opp)

            except (ValueError, TypeError, KeyError) as e:
                continue

        # Sort by edge score
        opportunities.sort(key=lambda x: x.edge_score, reverse=True)
        return opportunities[:max_results]

    def _calculate_edge_score(
        self, market: dict, volume: float, liquidity: float
    ) -> float:
        """Calculate edge score (higher = better opportunity)."""
        score = 50.0

        # Lower volume = potentially less efficient = edge
        if volume < 50000:
            score += 15
        elif volume < 100000:
            score += 10
        elif volume > 1000000:
            score -= 10

        # Low liquidity = potential edge
        if liquidity < 10000:
            score += 10
        elif liquidity < 50000:
            score += 5

        # Check for obscure category
        category = market.get("groupItemTitle") or market.get("category") or ""
        if category and any(
            x in category.lower() for x in ["obscure", "international", "minor"]
        ):
            score += 10

        return min(max(score, 0), 100)

    def _classify_risk(self, multiplier: float) -> RiskTier:
        if multiplier >= 1000:
            return RiskTier.YOLO
        elif multiplier >= 100:
            return RiskTier.MOONSHOT
        elif multiplier >= 20:
            return RiskTier.LONGSHOT
        else:
            return RiskTier.VALUE

    def _generate_reasoning(
        self, market: dict, edge_score: float, volume: float
    ) -> str:
        parts = []

        if edge_score >= 70:
            parts.append("HIGH EDGE")
        elif edge_score >= 50:
            parts.append("MODERATE EDGE")

        if volume < 100000:
            parts.append("low volume (less efficient)")

        return " | ".join(parts) if parts else "standard opportunity"


class CompoundCalculator:
    """Calculate compound betting strategy."""

    @staticmethod
    def calculate_strategy(
        starting_capital: float,
        target: float,
        max_stages: int = 5,
    ) -> CompoundStrategy:
        required_multiplier = target / starting_capital

        for stages in range(1, max_stages + 1):
            per_stage = required_multiplier ** (1 / stages)

            if per_stage <= 50:
                return CompoundStrategy(
                    starting_capital=starting_capital,
                    target=target,
                    required_multiplier=required_multiplier,
                    recommended_stages=stages,
                    per_stage_multiplier=per_stage,
                    current_capital=starting_capital,
                )

        return CompoundStrategy(
            starting_capital=starting_capital,
            target=target,
            required_multiplier=required_multiplier,
            recommended_stages=max_stages,
            per_stage_multiplier=required_multiplier ** (1 / max_stages),
            current_capital=starting_capital,
        )

    @staticmethod
    def get_stage_targets(strategy: CompoundStrategy) -> list[dict]:
        targets = []
        current = strategy.starting_capital

        for stage in range(1, strategy.recommended_stages + 1):
            next_target = current * strategy.per_stage_multiplier
            targets.append(
                {
                    "stage": stage,
                    "start": current,
                    "target": next_target,
                    "multiplier_needed": strategy.per_stage_multiplier,
                    "status": (
                        "COMPLETED"
                        if stage < strategy.current_stage
                        else (
                            "CURRENT" if stage == strategy.current_stage else "PENDING"
                        )
                    ),
                }
            )
            current = next_target

        return targets

    @staticmethod
    def recommend_positions(
        opportunities: list[MoonshotOpportunity],
        capital: float,
        target_multiplier: float,
        max_positions: int = 10,
    ) -> list[dict]:
        viable = [
            o
            for o in opportunities
            if o.potential_multiplier >= target_multiplier * 0.5
        ]

        if not viable:
            viable = opportunities[:max_positions]

        positions = []
        allocation_per_position = capital / min(len(viable), max_positions)

        for opp in viable[:max_positions]:
            shares = allocation_per_position / opp.price
            potential_value = shares * 1.0

            positions.append(
                {
                    "market_id": opp.market_id,
                    "question": opp.question[:60],
                    "side": opp.side,
                    "price": opp.price,
                    "allocation": allocation_per_position,
                    "shares": shares,
                    "potential_value": potential_value,
                    "potential_multiplier": potential_value / allocation_per_position,
                    "edge_score": opp.edge_score,
                    "risk_tier": opp.risk_tier.value,
                    "days_left": opp.days_to_expiry,
                    "url": f"https://polymarket.com/event/{opp.slug}",
                }
            )

        return positions


async def run_moonshot_dashboard(
    starting_capital: float = 50.0,
    target: float = 100000.0,
    max_price: float = 0.05,
    min_volume: float = 10000,
):
    """Run the moonshot tracker dashboard."""
    client = PolymarketClient()

    try:
        tracker = MoonshotTracker(client)

        # Calculate strategy
        strategy = CompoundCalculator.calculate_strategy(starting_capital, target)
        stage_targets = CompoundCalculator.get_stage_targets(strategy)

        print("\n" + "=" * 70)
        print("MOONSHOT TRACKER - $50 -> $100K CHALLENGE")
        print("=" * 70)

        print(f"\nCOMPOUND STRATEGY")
        print(f"   Starting: ${starting_capital:,.2f}")
        print(f"   Target: ${target:,.2f}")
        print(f"   Required: {strategy.required_multiplier:,.0f}x total")
        print(f"   Stages: {strategy.recommended_stages}")
        print(f"   Per stage: {strategy.per_stage_multiplier:.1f}x")

        print(f"\nSTAGE BREAKDOWN")
        for t in stage_targets:
            status_icon = (
                "[X]"
                if t["status"] == "COMPLETED"
                else ("[>]" if t["status"] == "CURRENT" else "[ ]")
            )
            print(
                f"   {status_icon} Stage {t['stage']}: "
                f"${t['start']:,.2f} -> ${t['target']:,.2f} ({t['multiplier_needed']:.1f}x)"
            )

        # Find opportunities
        print(f"\nSCANNING FOR MOONSHOTS...")
        opportunities = await tracker.find_moonshots(
            max_price=max_price,
            min_volume=min_volume,
        )

        if not opportunities:
            print("\nNo opportunities found matching criteria.")
            print("Try adjusting --max-price or --min-volume")
            return

        print(f"\nTOP OPPORTUNITIES (by edge score)")
        print("-" * 70)

        tier_icons = {
            RiskTier.YOLO: "[YOLO]",
            RiskTier.MOONSHOT: "[MOON]",
            RiskTier.LONGSHOT: "[LONG]",
            RiskTier.VALUE: "[VAL] ",
        }

        for i, opp in enumerate(opportunities[:15], 1):
            tier_icon = tier_icons[opp.risk_tier]

            print(
                f"{i:2}. {tier_icon} ${opp.price:.4f} -> {opp.potential_multiplier:,.0f}x"
            )
            print(
                f"    Edge: {opp.edge_score:.0f}/100 | Vol: ${opp.volume:,.0f} | {opp.days_to_expiry:.0f}d"
            )
            print(f"    {opp.question[:65]}")
            print(f"    https://polymarket.com/event/{opp.slug}")
            print()

        # Recommend positions
        print(
            f"\nRECOMMENDED POSITIONS FOR STAGE 1 "
            f"(${starting_capital} -> ${starting_capital * strategy.per_stage_multiplier:.0f})"
        )
        print("-" * 70)

        positions = CompoundCalculator.recommend_positions(
            opportunities,
            capital=starting_capital,
            target_multiplier=strategy.per_stage_multiplier,
            max_positions=10,
        )

        for pos in positions:
            print(f"   ${pos['allocation']:.2f} -> {pos['side']} @ ${pos['price']:.4f}")
            print(
                f"   {pos['shares']:.1f} shares -> potential ${pos['potential_value']:.2f} "
                f"({pos['potential_multiplier']:.0f}x)"
            )
            print(f"   {pos['question']}")
            print(f"   {pos['url']}")
            print()

        total_potential = sum(p["potential_value"] for p in positions)
        print(f"   TOTAL POTENTIAL: ${total_potential:,.2f} (if ONE hits)")

        # Summary
        print("\n" + "=" * 70)
        print("REALITY CHECK")
        print("=" * 70)
        print(f"   * You're betting on {len(positions)} longshots")
        print(f"   * Most will lose (that's why they're cheap)")
        print(f"   * If ANY ONE hits, you profit")
        print(f"   * If none hit, you lose ${starting_capital}")
        print(f"   * This is gambling, not investing")
        print("=" * 70)

    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Moonshot Tracker - Find lottery tickets on Polymarket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python moonshot.py                      # Default: $50 -> $100k
    python moonshot.py --capital 100        # Start with $100
    python moonshot.py --target 50000       # Target $50k
    python moonshot.py --max-price 0.10     # Look at up to 10 cent contracts
    python moonshot.py --min-volume 50000   # Only markets with $50k+ volume
        """,
    )

    parser.add_argument(
        "--capital",
        "-c",
        type=float,
        default=50.0,
        help="Starting capital in USD (default: 50)",
    )
    parser.add_argument(
        "--target",
        "-t",
        type=float,
        default=100000.0,
        help="Target amount in USD (default: 100000)",
    )
    parser.add_argument(
        "--max-price",
        "-p",
        type=float,
        default=0.05,
        help="Maximum contract price to consider (default: 0.05 = 5 cents)",
    )
    parser.add_argument(
        "--min-volume",
        "-v",
        type=float,
        default=10000.0,
        help="Minimum market volume in USD (default: 10000)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_moonshot_dashboard(
            starting_capital=args.capital,
            target=args.target,
            max_price=args.max_price,
            min_volume=args.min_volume,
        )
    )


if __name__ == "__main__":
    main()
