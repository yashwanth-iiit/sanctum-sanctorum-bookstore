"""Contract boundaries and interactions not exercised by the supplied suite."""
from datetime import timedelta

import pytest

from app.services.loans import calculate_late_fee


@pytest.mark.parametrize("field", ["title", "author", "price_cents", "stock", "restricted"])
def test_explicit_patch_null_is_invalid_and_preserves_book(client, make_book, field):
    book = make_book()
    assert client.patch(f"/books/{book['id']}", json={field: None}).status_code == 422
    assert client.get(f"/books/{book['id']}").json() == book


def test_empty_and_unknown_only_patch_are_noops(client, make_book):
    book = make_book()
    for payload in ({}, {"isbn": None, "unknown": "ignored"}):
        response = client.patch(f"/books/{book['id']}", json=payload)
        assert response.status_code == 200
        assert response.json() == book


@pytest.mark.parametrize("isbn", ["９７８０００００００００２", "²" * 13])
def test_non_ascii_isbn_digits_return_422_instead_of_server_error(client, isbn):
    response = client.post("/books", json={
        "title": "Book", "author": "Author", "isbn": isbn, "price_cents": 0, "stock": 1,
    })
    assert response.status_code == 422


@pytest.mark.parametrize("needle", ["%", "_", "/"])
def test_search_treats_pattern_characters_as_literal_substrings(client, make_book, needle):
    match = make_book(title=f"A{needle}B")
    make_book(title="AB")
    make_book(title="AxxB")
    response = client.get("/books", params={"q": needle})
    assert [book["id"] for book in response.json()["items"]] == [match["id"]]


def test_zero_price_and_reversed_price_bounds(client, make_book):
    free = make_book(price_cents=0)
    make_book(price_cents=100)
    assert client.get("/books", params={"max_price": 0}).json()["items"] == [free]
    assert client.get("/books", params={"min_price": 100, "max_price": 0}).json()["total"] == 0


def test_member_name_length_is_measured_after_trimming(client):
    response = client.post("/members", json={"name": "   " + "N" * 100 + "   ", "email": "reader@example.com"})
    assert response.status_code == 201
    assert response.json()["name"] == "N" * 100


def test_purchase_and_borrowing_share_inventory(client, make_member, make_book):
    member = make_member(tier="master")
    book = make_book(stock=1)
    loan = client.post("/loans", json={"member_id": member["id"], "book_id": book["id"]}).json()
    order_payload = {"member_id": member["id"], "items": [{"book_id": book["id"], "quantity": 1}]}
    assert client.post("/orders", json=order_payload).status_code == 409
    assert client.post(f"/loans/{loan['id']}/return").status_code == 200
    order = client.post("/orders", json=order_payload).json()
    assert client.post("/loans", json={"member_id": member["id"], "book_id": book["id"]}).status_code == 409
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 200
    assert client.get(f"/books/{book['id']}").json()["stock"] == 1


@pytest.mark.parametrize("price_at_return", [0, 30, 10_000])
def test_late_fee_uses_current_price_and_is_then_frozen(client, clock, make_member, make_book, price_at_return):
    member = make_member()
    book = make_book(price_cents=1000)
    loan = client.post("/loans", json={"member_id": member["id"], "book_id": book["id"]}).json()
    clock.advance(days=16, microseconds=1)
    client.patch(f"/books/{book['id']}", json={"price_cents": price_at_return})
    returned = client.post(f"/loans/{loan['id']}/return").json()
    assert returned["late_fee_cents"] == min(75, price_at_return)
    client.patch(f"/books/{book['id']}", json={"price_cents": 9999})
    assert client.get(f"/loans/{loan['id']}").json()["late_fee_cents"] == returned["late_fee_cents"]


@pytest.mark.parametrize("elapsed,fee", [
    (timedelta(microseconds=1), 25),
    (timedelta(days=1), 25),
    (timedelta(days=1, microseconds=1), 50),
])
def test_fee_rounding_preserves_microsecond_boundary(clock, elapsed, fee):
    assert calculate_late_fee(clock.current, clock.current + elapsed, 1000) == fee


def test_report_uses_current_book_title(client, make_member, make_book):
    member = make_member()
    book = make_book(title="Original")
    order = client.post("/orders", json={"member_id": member["id"], "items": [{"book_id": book["id"], "quantity": 2}]}).json()
    client.post(f"/orders/{order['id']}/pay")
    client.patch(f"/books/{book['id']}", json={"title": "Renamed"})
    assert client.get("/reports/top-books").json() == [{"book_id": book["id"], "title": "Renamed", "copies_sold": 2}]


def test_stats_do_not_multiply_orders_by_loans_or_include_other_members(client, make_member, make_book):
    member = make_member(tier="supreme")
    other = make_member()
    book = make_book(price_cents=1000, stock=20)
    for owner, quantity in ((member, 1), (member, 2), (other, 3)):
        order = client.post("/orders", json={"member_id": owner["id"], "items": [{"book_id": book["id"], "quantity": quantity}]}).json()
        client.post(f"/orders/{order['id']}/pay")
    for _ in range(3):
        borrowed = make_book()
        assert client.post("/loans", json={"member_id": member["id"], "book_id": borrowed["id"]}).status_code == 201
    client.post("/loans", json={"member_id": other["id"], "book_id": book["id"]})
    assert client.get(f"/members/{member['id']}/stats").json() == {
        "member_id": member["id"], "orders_paid": 2, "total_spent_cents": 2550,
        "active_loans": 3, "overdue_loans": 0, "late_fees_cents": 0,
    }


def test_three_item_order_checks_all_access_before_any_stock_failure(client, make_member, make_book):
    member = make_member()
    unavailable = make_book(stock=0)
    ordinary = make_book()
    restricted = make_book(restricted=True)
    payload = {"member_id": member["id"], "items": [
        {"book_id": book["id"], "quantity": 1} for book in (unavailable, ordinary, restricted)
    ]}
    assert client.post("/orders", json=payload).status_code == 403
    payload["items"].append({"book_id": 99999, "quantity": 1})
    assert client.post("/orders", json=payload).status_code == 404
    assert client.get(f"/members/{member['id']}/orders").json() == []
    assert client.get(f"/books/{ordinary['id']}").json()["stock"] == ordinary["stock"]
