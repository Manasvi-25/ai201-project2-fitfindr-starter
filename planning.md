# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
It Looks through the listings dataset and finds items that match what the user described. It checks keywords against the title, description, category, and style tags, then sorts results by how many keywords matched. Price and size are used to filter things out before scoring.

**Input parameters:**
description (str): What the user is looking for (like "vintage graphic tee or a maxi dress"). Gets split into keywords and matched against listing fields.
size (str or None): Size to filter by (like "M"). None means skip the size filter.
max_price (float or None): Price ceiling in USD. None means no price limit.

**What it returns:**
A list of matching listing dicts sorted by relevance. Returns an empty list if nothing matches. 

**What happens if it fails or returns nothing:**
Returns []. The planning loop catches this, sets an error message like "Nothing matched — try broader keywords or a higher price limit", and stops there without calling the other tools.

---

### Tool 2: suggest_outfit

**What it does:**
 Takes the top search result and the user's wardrobe and asks the LLM to come up with 1-2 outfit ideas using the new piece with what they already own.

**Input parameters:**
new_item (dict): The top listing from search_listings.
wardrobe (dict): Has an items key with a list of wardrobe pieces. Each piece has name, category, colors, style_tags, notes.

**What it returns:**
A string with 1-2 outfit suggestions. If the wardrobe is empty it still works, it just gives general styling advice instead.

**What happens if it fails or returns nothing:**
If the LLM call fails it returns an error string. Empty wardrobe doesn't crash it, it handles it gracefully by skipping the wardrobe-specific pairing and gives general advice.

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion and the new item and generates a short casual caption.

**Input parameters:**
outfit (str): The suggestion string from suggest_outfit.
new_item (dict): The listing dict, used for price, platform, colors in the caption.

**What it returns:**
A 1-3 sentence lowercase caption with an emoji or two, mentions the price and platform. Varies each run.

**What happens if it fails or returns nothing:**
If outfit is empty it returns an error string right away without touching the LLM. LLM failure also returns an error string. 

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent calls search_listings first. If it comes back empty, it sets an error message in the session and stops, suggest_outfit never gets called with nothing. If there are results, it takes the top one, passes it into suggest_outfit along with the wardrobe, saves that output, then passes both into create_fit_card. Each step only runs if the previous one succeeded.

---

## State Management

**How does information from one tool get passed to the next?**
Everything lives in a session dict. search_listings puts its top result in session["selected_item"]. suggest_outfit reads that and puts its output in session["outfit_suggestion"]. create_fit_card reads both. The user never has to re-enter anything between steps. If something fails early, the later keys just stay None.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets session["error"] to "No listings found for '[query]' — try broader keywords, a different size, or a higher price limit." Stops the loop, never calls suggest_outfit. |
| suggest_outfit | Wardrobe is empty | Detects empty items list, skips wardrobe-specific pairings, prompts LLM for general styling advice instead. Returns a useful string, never crashes. |
| create_fit_card | Outfit input is missing or incomplete | Checks for empty string before calling LLM, returns "Can't create a fit card without an outfit — make sure suggest_outfit ran successfully." immediately. |

---

## Architecture

```
User query
    |
    v
Planning Loop
    |
    +--> search_listings(description, size, max_price)
            |
            +-- results == [] --> session["error"] = "No listings found..." --> return session
            |
            +-- results != []
                    |
                session["selected_item"] = results[0]
                    |
                suggest_outfit(selected_item, wardrobe)
                    |
                session["outfit_suggestion"] = "..."
                    |
                create_fit_card(outfit_suggestion, selected_item)
                    |
                session["fit_card"] = "..."
                    |
                    v
              return session

```
---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I'll use Claude. For each tool I'll paste in that tool's spec block from this file (inputs, return value, failure mode) plus the data_loader.py code so it knows what load_listings() and get_example_wardrobe() return. I'll ask it to implement one function at a time in tools.py. Before using any generated code I'll check that it filters by all three parameters, uses "name" not "title" for wardrobe items, and handles the failure mode I described. Then I'll test each tool directly from the terminal with 2-3 hardcoded inputs before moving on.

**Milestone 4 — Planning loop and state management:**

I'll use Claude. I'll give it the Architecture diagram and the Planning Loop + State Management sections from this file and ask it to implement run_agent() in agent.py. I'll verify the generated code actually branches on the search_listings result, if it calls all three tools unconditionally regardless of what search returns, it's wrong. I'll also check that values flow through the session dict and nothing is hardcoded between steps.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a knit cardigan. What's out there and how would I style it?"

**Step 1:**
search_listings("knit cardigan", size=None, max_price=None) runs. Keywords "knit" and "cardigan" get matched against title, description, category, and style_tags across all 40 listings. Top result is the Knit Cardigan-Chunky Brown, $35, depop, size One Size / Oversized, condition excellent. Agent saves this to session["selected_item"].

**Step 2:**
suggest_outfit runs with session["selected_item"] as new_item and the example wardrobe as wardrobe. The wardrobe has baggy dark-wash jeans, a white ribbed tank, chunky white sneakers, and black combat boots among its 10 items. LLM returns something like "Layer this chunky brown cardigan open over your white ribbed tank and baggy jeans with chunky sneakers for an easy cozy look, or belt it at the waist over straight leg trousers and combat boots for something more put together." Agent saves this to session["outfit_suggestion"].

**Step 3:**
create_fit_card runs with session["outfit_suggestion"] and session["selected_item"]. LLM generates something like "grabbed this chunky brown cardigan off depop for $35 and it goes with literally everything i own 🤎 tank + baggy jeans and done." Agent saves this to session["fit_card"].

**Final output to user:**
All three panels populate — the listing details for the chunky brown cardigan, the outfit suggestion, and the fit card caption ready to copy.
