# FitFindr — Starter Kit

A multi-tool AI agent that helps you find secondhand clothing and figure out how to style it. You describe what you're looking for, FitFindr searches the listings, suggests an outfit using your wardrobe, and generates a shareable caption for the look.


## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Open the URL shown in your terminal.

---

## Tool Inventory

### `search_listings(description, size, max_price)`
**Purpose:** Searches the 40-item listings dataset and returns items that match the user's description, filtered by size and price.

**Inputs:**
- `description` (str): Natural-language description of the item (e.g. "knit cardigan"). Split into keywords and matched against each listing's title, description, category, and style_tags.
- `size` (str or None): Size to filter by (e.g. "M"). Case-insensitive partial match, so "M" matches "S/M". Pass None to skip size filtering.
- `max_price` (float or None): Price ceiling in USD. Pass None for no price limit.

**Returns:** A list of matching listing dicts sorted by relevance score (most keyword matches first, price as tiebreaker). Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns an empty list `[]` if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`
**Purpose:** Takes the top search result and the user's wardrobe and asks the Groq LLM to suggest 1-2 complete outfit combinations.

**Inputs:**
- `new_item` (dict): A single listing dict from `search_listings`.
- `wardrobe` (dict): A wardrobe dict with an `items` key containing a list of wardrobe item dicts. Each wardrobe item has: `id`, `name`, `category`, `colors`, `style_tags`, `notes`.

**Returns:** A non-empty string with outfit suggestions. If the wardrobe is empty, returns general styling advice instead of wardrobe-specific pairings. Returns an error string if the LLM call fails.

---

### `create_fit_card(outfit, new_item)`
**Purpose:** Generates a short, casual Instagram-style caption for the thrift find and outfit.

**Inputs:**
- `outfit` (str): The outfit suggestion string from `suggest_outfit`.
- `new_item` (dict): The listing dict for the thrifted item, used for price, platform, and color details.

**Returns:** A 1-2 sentence lowercase caption with 1-2 emojis that mentions the price and platform. Output varies each run due to high LLM temperature. Returns a descriptive error string if `outfit` is empty.

---

## How the Planning Loop Works

The agent runs a conditional sequence — it does not call all three tools unconditionally every time.

1. The user's query is parsed with regex to extract a description, size, and max_price.
2. `search_listings` runs first. The agent then checks the result:
   - If `results == []`: the agent sets `session["error"]` to a specific message telling the user what was searched and what to try differently, then **returns immediately**. `suggest_outfit` and `create_fit_card` are never called.
   - If `results != []`: the agent takes `results[0]` as the selected item and continues.
3. `suggest_outfit` runs with the selected item and the user's wardrobe. The result is stored in the session.
4. `create_fit_card` runs with the outfit suggestion and selected item. The result is stored in the session.
5. The completed session is returned.

The key decision point is after `search_listings`. The agent's behavior is different depending on what comes back — it never calls `suggest_outfit` with empty input.

---

## State Management

All state lives in a session dict initialized at the start of each interaction. Nothing is re-entered by the user between steps.

| Key | Set by | Used by |
|-----|--------|---------|
| `session["parsed"]` | `run_agent` (regex parsing) | `search_listings` call |
| `session["search_results"]` | `search_listings` | planning loop (empty check) |
| `session["selected_item"]` | planning loop (`results[0]`) | `suggest_outfit`, `create_fit_card` |
| `session["outfit_suggestion"]` | `suggest_outfit` | `create_fit_card` |
| `session["fit_card"]` | `create_fit_card` | returned to UI |
| `session["error"]` | planning loop (on empty results) | UI (shown in first panel) |

If the flow stops early, `outfit_suggestion` and `fit_card` stay `None`.

---

## Error Handling

### `search_listings` — no results
If the dataset has no matches for the query, size, and price combination, the tool returns `[]`. The planning loop catches this and sets a specific error message:

> "No listings found for 'designer ballgown' in size XXS under $5 — try broader keywords, a different size, or a higher price limit."

The agent stops here. `suggest_outfit` never runs.

**Tested:**
```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
# Output: []
```

### `suggest_outfit` — empty wardrobe
If `wardrobe["items"]` is empty, the tool detects this before building the prompt and switches to a general styling advice prompt instead of wardrobe-specific pairings. Returns a useful string, never crashes.

**Tested:**
```bash
python -c "
from tools import search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(suggest_outfit(results[0], get_empty_wardrobe()))
"
# Output: general styling advice string, no exception
```

### `create_fit_card` — empty outfit string
If `outfit` is an empty or whitespace-only string, the tool returns an error message immediately without touching the LLM:

> "Error: can't create a fit card without an outfit — make sure suggest_outfit ran successfully."

**Tested:**
```bash
python -c "
from tools import search_listings, create_fit_card
results = search_listings('vintage graphic tee', size=None, max_price=50)
print(create_fit_card('', results[0]))
"
# Output: error string, no exception
```

---

## Spec Reflection

**One way the spec helped:** I think the planning.md helped me a lot in visualizing the project. Filling out the planning loop section in `planning.md` before writing any code made the branching logic in `run_agent()` straightforward to implement. The exact conditionL check `results == []` after `search_listings` and return early was already written out in plain English, so the code just translated it directly.

**One way implementation diverged from the spec:** The spec assumed size filtering would be a simple exact match (e.g. "M" == "M"). In the actual dataset, sizes are inconsistent, some listings use "S/M", "One Size / Oversized", or "W30 L30" instead of a single letter. The implementation uses a partial/substring match instead of exact equality so that "M" matches "S/M" and size filtering still works usefully across the dataset.

---
## AI Usage

**Instance 1 — `tools.py` implementation:**
I gave Claude the spec for each tool from `planning.md` one at a time — the inputs, what it returns, and what happens on failure. I also pasted in `data_loader.py` so it knew what `load_listings()` actually returns. I checked the code before running it — mainly that `suggest_outfit` used `"name"` not `"title"` for wardrobe items since that tripped me up earlier. The fit card output was way too long at first, more like a product description than a caption, so I rewrote the prompt myself to keep it to 1-2 sentences with the lowercase and emoji style.

**Instance 2 — `agent.py` planning loop:**
I gave Claude the architecture diagram and the planning loop and state management sections from `planning.md` and asked it to write `run_agent()`. I checked that it actually branched on the search result and didn't just call all three tools every time regardless. I also had to tweak the size matching myself — the generated code did exact match but the dataset has sizes like "S/M" and "One Size / Oversized" so exact match would miss most things. Changed it to a substring match so "M" would still catch "S/M".
