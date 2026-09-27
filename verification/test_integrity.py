"""Fault injection verifies durable state, not just returned HTTP responses."""
import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Book, Loan, Member, Order, OrderItem
from app.schemas import BookCreate, BookUpdate, LoanCreate, MemberCreate, OrderCreate
from app.services import books, loans, members, orders
from tests.conftest import isbn13


def snapshot(db):
    with Session(db.get_bind()) as observer:
        return {
            model.__tablename__: list(observer.execute(select(model.__table__).order_by(model.id)))
            for model in (Book, Member, Order, OrderItem, Loan)
        }


@pytest.mark.parametrize("failure_event", ["before_commit", "after_flush"])
@pytest.mark.parametrize("operation", [
    "create_order", "cancel_order", "pay_order", "create_loan",
    "return_loan", "update_book", "create_book", "create_member",
])
def test_failed_write_rolls_back_every_persisted_change(db, clock, operation, failure_event):
    member = members.create_member(db, MemberCreate(name="Reader", email="reader@example.com", tier="supreme"), clock.current)
    book = books.create_book(db, BookCreate(title="First", author="Author", isbn=isbn13(800), price_cents=1000, stock=5))
    second = books.create_book(db, BookCreate(title="Second", author="Author", isbn=isbn13(801), price_cents=500, stock=3))
    order_data = OrderCreate(member_id=member.id, items=[
        {"book_id": book.id, "quantity": 2}, {"book_id": second.id, "quantity": 1},
    ])
    loan_data = LoanCreate(member_id=member.id, book_id=book.id)
    if operation in ("cancel_order", "pay_order"):
        order = orders.create_order(db, order_data, clock.current)
    if operation == "return_loan":
        loan = loans.create_loan(db, loan_data, clock.current)
        clock.advance(days=16, seconds=1)
    before = snapshot(db)

    def fail_write(*args):
        raise RuntimeError("Injected database failure")

    event.listen(db, failure_event, fail_write, once=True)
    actions = {
        "create_order": lambda: orders.create_order(db, order_data, clock.current),
        "cancel_order": lambda: orders.cancel_order(db, order.id),
        "pay_order": lambda: orders.pay_order(db, order.id),
        "create_loan": lambda: loans.create_loan(db, loan_data, clock.current),
        "return_loan": lambda: loans.return_loan(db, loan.id, clock.current),
        "update_book": lambda: books.update_book(db, book.id, BookUpdate(stock=42, title="Changed")),
        "create_book": lambda: books.create_book(db, BookCreate(title="New", author="Author", isbn=isbn13(802), price_cents=100, stock=1)),
        "create_member": lambda: members.create_member(db, MemberCreate(name="New", email="new@example.com"), clock.current),
    }
    with pytest.raises(RuntimeError, match="Injected database failure"):
        actions[operation]()
    assert not db.in_transaction()
    assert snapshot(db) == before
    # A rollback leaves the same request session usable for subsequent operations.
    assert db.get(Book, book.id).stock == before["books"][0].stock


@pytest.mark.parametrize("entity", ["book", "member"])
def test_unique_constraint_conflict_after_precheck_returns_409(db, clock, entity):
    from fastapi import HTTPException

    def insert_competing_row(session, *args):
        with Session(session.get_bind()) as competitor:
            if entity == "book":
                competitor.add(Book(title="Competing", author="Author", isbn=isbn13(900), price_cents=100, stock=2, restricted=False))
            else:
                competitor.add(Member(name="Competing", email="same@example.com", tier="apprentice", created_at=clock.current))
            competitor.commit()

    event.listen(db, "before_flush", insert_competing_row, once=True)
    with pytest.raises(HTTPException) as error:
        if entity == "book":
            books.create_book(db, BookCreate(title="Reader", author="Author", isbn=isbn13(900), price_cents=100, stock=2))
        else:
            members.create_member(db, MemberCreate(name="Reader", email="same@example.com"), clock.current)
    assert error.value.status_code == 409
    assert len(snapshot(db)["books" if entity == "book" else "members"]) == 1


def test_unrelated_integrity_error_is_not_reported_as_duplicate(db):
    def fail_write(*args):
        raise IntegrityError("INSERT", {}, ValueError("Unrelated constraint failure"))

    event.listen(db, "before_flush", fail_write, once=True)
    with pytest.raises(IntegrityError):
        books.create_book(db, BookCreate(title="Reader", author="Author", isbn=isbn13(901), price_cents=100, stock=2))
    assert snapshot(db)["books"] == []
