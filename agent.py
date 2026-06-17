"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    import re

    session = _new_session(query, wardrobe)

    # Step 2: parse query for description, size, max_price
    q = query.lower()

    # extract max_price — looks for "under $40" or "$40" or "under 40"
    price_match = re.search(r'under\s*\$?(\d+(\.\d+)?)', q)
    max_price = float(price_match.group(1)) if price_match else None

    # extract size — looks for "size M" or "in M" or standalone S/M/L/XL etc
    size_match = re.search(r'\bsize\s*([a-zA-Z0-9/]+)\b', q) or \
                 re.search(r'\bin\s+(xs|s|m|l|xl|xxl|\d+)\b', q)
    size = size_match.group(1).upper() if size_match else None

    # strip out price/size fragments to get clean description
    description = re.sub(r'under\s*\$?\d+(\.\d+)?', '', q)
    description = re.sub(r'\bsize\s*[a-zA-Z0-9/]+', '', description)
    description = re.sub(r'\bin\s+(xs|s|m|l|xl|xxl|\d+)\b', '', description)
    description = re.sub(r"[^a-z0-9 ]", '', description).strip()

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # Step 3: search
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    if not results:
        session["error"] = (
            f"No listings found for '{description}'"
            + (f" in size {size}" if size else "")
            + (f" under ${max_price:.0f}" if max_price else "")
            + " — try broader keywords, a different size, or a higher price limit."
        )
        return session

    # Step 4: select top result
    session["selected_item"] = results[0]

    # Step 5: suggest outfit
    session["outfit_suggestion"] = suggest_outfit(results[0], wardrobe)

    # Step 6: fit card
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], results[0])

    # Step 7: return
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
