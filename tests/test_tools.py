from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings tests ─────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("denim shorts", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("flared maxi dress", size="XS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("flannel shirt", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)

def test_search_no_description():
    results = search_listings("", size=None, max_price=None)
    assert results == []

# ── suggest_outfit tests ──────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    results = search_listings("knit cardigan", size=None, max_price=None)
    assert len(results) > 0
    suggestion = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0
    assert not suggestion.startswith("Error")

def test_suggest_outfit_empty_wardrobe():
    results = search_listings("knit cardigan", size=None, max_price=None)
    assert len(results) > 0
    suggestion = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0
    assert not suggestion.startswith("Error")


# ── create_fit_card tests ─────────────────────────────────────────────────────

def test_fit_card_empty_outfit():
    results = search_listings("knit cardigan", size=None, max_price=None)
    result = create_fit_card("", results[0])
    assert "Error" in result

def test_fit_card_returns_caption():
    results = search_listings("knit cardigan", size=None, max_price=None)
    suggestion = suggest_outfit(results[0], get_example_wardrobe())
    card = create_fit_card(suggestion, results[0])
    assert isinstance(card, str)
    assert len(card) > 0
    assert not card.startswith("Error")