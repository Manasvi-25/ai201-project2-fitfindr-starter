"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    try:
        listings = load_listings()
    except Exception as e:
        print(f"[search_listings] Failed to load listings: {e}")
        return []

    if not description or not description.strip():
        return []

    keywords = [kw.lower() for kw in description.strip().split()]
    results = []

    for item in listings:
        # hard filter: price
        if max_price is not None and item.get("price", 0) > max_price:
            continue

        # hard filter: size (case-insensitive, partial match so "M" matches "S/M")
        if size is not None:
            item_size = item.get("size", "").lower()
            if size.lower() not in item_size:
                continue

        # score by keyword overlap
        searchable = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            " ".join(item.get("style_tags", [])),
        ]).lower()

        score = sum(1 for kw in keywords if kw in searchable)

        if score > 0:
            results.append({**item, "_score": score})

    results.sort(key=lambda x: (-x["_score"], x.get("price", 0)))

    for r in results:
        r.pop("_score", None)

    return results


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    if not new_item:
        return "Error: no item provided to suggest_outfit."

    wardrobe_items = wardrobe.get("items", [])

    if wardrobe_items:
        wardrobe_lines = "\n".join(
            f"- {w.get('name', 'unknown')} ({w.get('category', '')}, {', '.join(w.get('colors', []))})"
            for w in wardrobe_items
        )
        wardrobe_section = f"Their current wardrobe:\n{wardrobe_lines}"
        wardrobe_instruction = "Suggest 1-2 specific outfit combinations using the new item with named pieces from their wardrobe."
    else:
        wardrobe_section = "They don't have a wardrobe entered yet."
        wardrobe_instruction = "Since there's no wardrobe, give general styling advice — what kinds of pieces pair well with this item and what vibe it suits."

    prompt = f"""You are a creative thrift-fashion stylist.

The user just found this secondhand item:
- Title: {new_item.get('title', 'Unknown')}
- Description: {new_item.get('description', '')}
- Category: {new_item.get('category', '')}
- Style tags: {', '.join(new_item.get('style_tags', []))}
- Colors: {', '.join(new_item.get('colors', []))}
- Condition: {new_item.get('condition', '')}

{wardrobe_section}

{wardrobe_instruction}
Be specific, practical, and keep it under 100 words."""

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: could not generate outfit suggestion ({e})."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Error: can't create a fit card without an outfit — make sure suggest_outfit ran successfully."

    if not new_item:
        return "Error: no item provided to create_fit_card."

    prompt = f"""You are writing a casual Instagram caption for a thrift-fashion post.

The thrifted item:
- Title: {new_item.get('title', 'Unknown')}
- Price: ${new_item.get('price', '?')}
- Platform: {new_item.get('platform', 'a thrift store')}
- Colors: {', '.join(new_item.get('colors', []))}

The outfit:
{outfit}

Write a 2-4 sentence caption. Rules:
- All lowercase
- 1-2 emojis
- Mention the price and platform naturally once each
- Sound like a real person posting their OOTD, not a product description
- Be specific about the vibe
- No hashtags"""

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: could not generate fit card ({e})."