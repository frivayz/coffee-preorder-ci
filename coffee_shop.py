"""Доменная логика сервиса предзаказа кофе CF-01 «Предзаказ кофе».

Заказчик: бизнес-центр «Северный» (ТЗ TZ-CF-01-v1.0).
Модуль реализует функциональные требования FR-01…FR-06:
предзаказ из меню, время готовности, отмена до начала приготовления,
уведомление о стоп-позиции с предложением замены и лимит позиций в заказе.

ВНИМАНИЕ: starter-версия модуля намеренно содержит скрытые дефекты.
Их должны поймать модульные тесты (test_coffee_shop.py)
и CI-конвейер (.github/workflows/ci.yml).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

MAX_ITEMS_PER_ORDER: int = 3
DEFAULT_REPLACEMENTS: int = 2


class OrderError(Exception):
    """Базовая ошибка доменной логики предзаказа."""


class PositionNotFoundError(OrderError):
    """Позиции нет в меню (FR-01)."""


class PositionUnavailableError(OrderError):
    """Позиция в стоп-листе; содержит предложенные замены (FR-04)."""

    def __init__(self, position: str, suggestions: list[str]) -> None:
        replacements = ", ".join(suggestions) or "—"
        super().__init__(f"Позиция «{position}» закончилась. Замены: {replacements}")
        self.position = position
        self.suggestions = suggestions


class OrderLimitError(OrderError):
    """Превышен лимит позиций в одном заказе (FR-06)."""


class OrderStateError(OrderError):
    """Действие недопустимо в текущем статусе заказа."""


class CancelNotAllowedError(OrderStateError):
    """Отмена заказа после старта приготовления запрещена (FR-03)."""


class OrderNotFoundError(OrderError):
    """Заказа с таким номером нет."""


class OrderStatus(Enum):
    """Жизненный цикл заказа."""

    ACCEPTED = "Принят"
    PREPARING = "Готовится"
    READY = "Готов"
    CANCELLED = "Отменён"


@dataclass(frozen=True)
class Position:
    """Позиция меню."""

    name: str
    price: float
    prep_minutes: int
    category: str = "coffee"

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError("Цена позиции не может быть отрицательной")
        if self.prep_minutes < 1:
            raise ValueError("Время приготовления должно быть не меньше минуты")


@dataclass
class Order:
    """Предзаказ сотрудника."""

    number: int
    items: list[Position] = field(default_factory=list)
    status: OrderStatus = OrderStatus.ACCEPTED


class CoffeeShop:
    """Сервис предзаказа: каталог, стоп-лист и очередь заказов бариста."""

    def __init__(self, menu: list[Position], stop_list: list[str] | None = None) -> None:
        self._menu: dict[str, Position] = {position.name: position for position in menu}
        self._stop_list: set[str] = set(stop_list or [])
        self._orders: dict[int, Order] = {}
        self._next_number: int = 1

    # --- Каталог и стоп-лист (FR-01, FR-04) ---------------------------------

    def menu_positions(self) -> list[Position]:
        """Весь каталог позиций (FR-01)."""
        return list(self._menu.values())

    def available_positions(self) -> list[Position]:
        """Позиции, доступные к предзаказу: каталог без стоп-листа (FR-04)."""
        # БАГ ДЛЯ СТУДЕНТОВ: стоп-лист не учитывается, доступны все позиции
        return list(self._menu.values())

    def find_replacements(self, name: str, limit: int = DEFAULT_REPLACEMENTS) -> list[str]:
        """Подбирает замены для недоступной позиции: сначала позиции той же категории."""
        target = self._menu.get(name)
        available = [p for p in self.available_positions() if p.name != name]
        if target is not None:
            same_category = [p.name for p in available if p.category == target.category]
            if same_category:
                return same_category[:limit]
        return [p.name for p in available][:limit]

    def stop_position(self, name: str) -> None:
        """Ставит позицию в стоп-лист."""
        if name not in self._menu:
            raise PositionNotFoundError(f"Позиции «{name}» нет в меню")
        self._stop_list.add(name)

    def resume_position(self, name: str) -> None:
        """Убирает позицию из стоп-листа."""
        self._stop_list.discard(name)

    # --- Заказы (FR-01, FR-02, FR-03, FR-06) --------------------------------

    def create_order(self, position_names: list[str]) -> Order:
        """Создаёт предзаказ из списка названий позиций (FR-01)."""
        if len(position_names) > MAX_ITEMS_PER_ORDER:
            raise OrderLimitError(
                f"В одном заказе не может быть больше {MAX_ITEMS_PER_ORDER} позиций"
            )
        for name in position_names:
            self._validate_position(name)

        order = Order(number=self._next_number)
        self._next_number += 1
        self._orders[order.number] = order
        for name in position_names:
            self.add_item(order.number, name)
        return order

    def add_item(self, order_number: int, name: str) -> Order:
        """Добавляет позицию в существующий заказ (FR-01, FR-06)."""
        order = self.get_order(order_number)
        if order.status is not OrderStatus.ACCEPTED:
            raise OrderStateError(f"Нельзя изменить заказ в статусе «{order.status.value}»")
        self._validate_position(name)

        # БАГ ДЛЯ СТУДЕНТОВ: граница лимита проверяется неверно —
        # четвёртая позиция проходит проверку (FR-06)
        if len(order.items) > MAX_ITEMS_PER_ORDER:
            raise OrderLimitError(
                f"В одном заказе не может быть больше {MAX_ITEMS_PER_ORDER} позиций"
            )

        order.items.append(self._menu[name])
        return order

    def cancel_order(self, order_number: int) -> Order:
        """Отменяет заказ до начала приготовления (FR-03)."""
        order = self.get_order(order_number)
        # БАГ ДЛЯ СТУДЕНТОВ: не проверяется статус —
        # можно отменить заказ, который уже готовится или готов
        order.status = OrderStatus.CANCELLED
        return order

    def start_preparing(self, order_number: int) -> Order:
        """Бариста начал готовить заказ (FR-02)."""
        order = self.get_order(order_number)
        if order.status is not OrderStatus.ACCEPTED:
            raise OrderStateError(f"Нельзя начать готовить заказ в статусе «{order.status.value}»")
        order.status = OrderStatus.PREPARING
        return order

    def mark_ready(self, order_number: int) -> Order:
        """Бариста подтвердил готовность заказа вручную (допущение ТЗ)."""
        order = self.get_order(order_number)
        if order.status is not OrderStatus.PREPARING:
            raise OrderStateError(f"Нельзя завершить заказ в статусе «{order.status.value}»")
        order.status = OrderStatus.READY
        return order

    def readiness_message(self, order_number: int) -> str | None:
        """Сообщение о времени готовности вида «~5 мин» (FR-02).

        Позиции готовятся параллельно, поэтому время заказа —
        максимум по времени приготовления его позиций.
        """
        order = self.get_order(order_number)
        if order.status is not OrderStatus.PREPARING or not order.items:
            return None
        minutes = max(item.prep_minutes for item in order.items)
        return f"~{minutes} мин"

    def order_total(self, order_number: int) -> float:
        """Стоимость заказа в рублях (FR-01)."""
        order = self.get_order(order_number)
        # БАГ ДЛЯ СТУДЕНТОВ: одинаковые позиции схлопываются —
        # set вместо list, две «Латте» считаются как одна
        return round(sum({item.price for item in order.items}), 2)

    def queue(self) -> list[Order]:
        """Очередь бариста: принятые и готовящиеся заказы (FR-01, FR-02)."""
        return [
            order
            for order in self._orders.values()
            if order.status in (OrderStatus.ACCEPTED, OrderStatus.PREPARING)
        ]

    def get_order(self, order_number: int) -> Order:
        """Возвращает заказ по номеру."""
        try:
            return self._orders[order_number]
        except KeyError as exc:
            raise OrderNotFoundError(f"Заказ №{order_number} не найден") from exc

    def _validate_position(self, name: str) -> None:
        """Проверяет, что позиция есть в меню и не в стоп-листе."""
        if name not in self._menu:
            raise PositionNotFoundError(f"Позиции «{name}» нет в меню")
        if name in self._stop_list:
            raise PositionUnavailableError(name, self.find_replacements(name))
