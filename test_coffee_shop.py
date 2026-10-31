"""Модульные тесты сервиса предзаказа кофе CF-01.

Тесты описывают ожидаемое (правильное) поведение системы по ТЗ TZ-CF-01-v1.0.
На starter-версии coffee_shop.py часть тестов падает — это и есть «красный»
статус сборки, который должен поймать CI-конвейер.
"""

from __future__ import annotations

import pytest

from coffee_shop import (
    MAX_ITEMS_PER_ORDER,
    CancelNotAllowedError,
    CoffeeShop,
    OrderLimitError,
    OrderNotFoundError,
    OrderStateError,
    OrderStatus,
    Position,
    PositionNotFoundError,
    PositionUnavailableError,
)


@pytest.fixture()
def menu() -> list[Position]:
    """Меню кофейни бизнес-центра."""
    return [
        Position("Эспрессо", 150.0, 2, "coffee"),
        Position("Латте", 220.0, 4, "coffee"),
        Position("Капучино", 210.0, 4, "coffee"),
        Position("Зелёный чай", 120.0, 3, "tea"),
        Position("Апельсиновый сок", 180.0, 1, "juice"),
    ]


@pytest.fixture()
def shop(menu: list[Position]) -> CoffeeShop:
    """Кофейня, в которой закончился зелёный чай."""
    return CoffeeShop(menu, stop_list=["Зелёный чай"])


# --- Каталог и стоп-лист ----------------------------------------------------


def test_menu_contains_all_positions(shop: CoffeeShop, menu: list[Position]) -> None:
    """FR-01: сотрудник видит всё меню кофейни."""
    assert len(shop.menu_positions()) == len(menu)


def test_available_positions_exclude_stop_list(shop: CoffeeShop) -> None:
    """FR-04: позиции из стоп-листа недоступны к предзаказу."""
    names = [position.name for position in shop.available_positions()]
    assert "Зелёный чай" not in names


def test_unavailable_position_offers_replacements(shop: CoffeeShop) -> None:
    """FR-04: вместо стоп-позиции предлагается замена."""
    with pytest.raises(PositionUnavailableError) as exc_info:
        shop.create_order(["Зелёный чай"])

    assert exc_info.value.position == "Зелёный чай"
    assert exc_info.value.suggestions, "замена должна быть предложена"
    assert "Зелёный чай" not in exc_info.value.suggestions


def test_stop_position_blocks_ordering(shop: CoffeeShop) -> None:
    """FR-04: позиция, ушедшая в стоп-лист, перестаёт приниматься."""
    shop.stop_position("Латте")
    with pytest.raises(PositionUnavailableError):
        shop.create_order(["Латте"])

    shop.resume_position("Латте")
    assert shop.create_order(["Латте"]).items[0].name == "Латте"


def test_stop_unknown_position_is_rejected(shop: CoffeeShop) -> None:
    """Негативный сценарий: нельзя остановить позицию вне меню."""
    with pytest.raises(PositionNotFoundError):
        shop.stop_position("Борщ")


# --- Оформление заказа (FR-01, FR-06) --------------------------------------


def test_create_order_from_menu(shop: CoffeeShop) -> None:
    """FR-01: заказ создаётся выбором позиций из меню."""
    order = shop.create_order(["Латте", "Эспрессо"])

    assert order.status is OrderStatus.ACCEPTED
    assert [item.name for item in order.items] == ["Латте", "Эспрессо"]


def test_create_order_with_unknown_position(shop: CoffeeShop) -> None:
    """Негативный сценарий: позиции нет в меню."""
    with pytest.raises(PositionNotFoundError):
        shop.create_order(["Борщ"])


def test_order_limit_allows_three_positions(shop: CoffeeShop) -> None:
    """FR-06 (граничное значение): ровно три позиции разрешены."""
    order = shop.create_order(["Латте", "Эспрессо", "Капучино"])

    assert len(order.items) == MAX_ITEMS_PER_ORDER


def test_order_limit_rejects_fourth_position(shop: CoffeeShop) -> None:
    """FR-06 (граничное значение): четвёртая позиция отклоняется."""
    order = shop.create_order(["Латте", "Эспрессо", "Капучино"])

    with pytest.raises(OrderLimitError):
        shop.add_item(order.number, "Апельсиновый сок")


def test_cannot_add_item_to_preparing_order(shop: CoffeeShop) -> None:
    """Негативный сценарий: после старта приготовления заказ не меняется."""
    order = shop.create_order(["Латте"])
    shop.start_preparing(order.number)

    with pytest.raises(OrderStateError):
        shop.add_item(order.number, "Эспрессо")


def test_unknown_order_raises(shop: CoffeeShop) -> None:
    """Негативный сценарий: заказа с таким номером нет."""
    with pytest.raises(OrderNotFoundError):
        shop.get_order(999)


# --- Стоимость (FR-01) ------------------------------------------------------


def test_order_total_sums_every_position(shop: CoffeeShop) -> None:
    """FR-01: каждая позиция заказа входит в стоимость, включая повторы."""
    order = shop.create_order(["Латте", "Латте", "Эспрессо"])

    assert shop.order_total(order.number) == pytest.approx(590.0)


# --- Отмена заказа (FR-03) --------------------------------------------------


def test_cancel_accepted_order(shop: CoffeeShop) -> None:
    """FR-03: принятый заказ отменяется."""
    order = shop.create_order(["Латте"])

    assert shop.cancel_order(order.number).status is OrderStatus.CANCELLED


def test_cancel_after_preparing_is_rejected(shop: CoffeeShop) -> None:
    """FR-03: отменить заказ после начала приготовления нельзя."""
    order = shop.create_order(["Латте"])
    shop.start_preparing(order.number)

    with pytest.raises(CancelNotAllowedError):
        shop.cancel_order(order.number)
    assert order.status is OrderStatus.PREPARING


def test_cancel_ready_order_is_rejected(shop: CoffeeShop) -> None:
    """FR-03: готовый заказ отменить нельзя."""
    order = shop.create_order(["Апельсиновый сок"])
    shop.start_preparing(order.number)
    shop.mark_ready(order.number)

    with pytest.raises(CancelNotAllowedError):
        shop.cancel_order(order.number)


# --- Очередь и время готовности (FR-02) ------------------------------------


def test_readiness_message_while_preparing(shop: CoffeeShop) -> None:
    """FR-02: сотрудник видит время готовности, пока заказ готовится."""
    order = shop.create_order(["Латте", "Эспрессо"])

    assert shop.readiness_message(order.number) is None
    shop.start_preparing(order.number)
    assert shop.readiness_message(order.number) == "~4 мин"


def test_readiness_message_is_none_after_ready(shop: CoffeeShop) -> None:
    """FR-02: после готовности сообщение о времени больше не нужно."""
    order = shop.create_order(["Апельсиновый сок"])
    shop.start_preparing(order.number)
    shop.mark_ready(order.number)

    assert shop.readiness_message(order.number) is None


def test_queue_contains_only_active_orders(shop: CoffeeShop) -> None:
    """FR-01: в очереди бариста только принятые и готовящиеся заказы."""
    active = shop.create_order(["Латте"])
    cancelled = shop.create_order(["Эспрессо"])
    shop.cancel_order(cancelled.number)

    assert [order.number for order in shop.queue()] == [active.number]
