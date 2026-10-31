"""Демонстрация работы сервиса предзаказа кофе CF-01 «Предзаказ кофе».

Запуск: python demo.py
"""

from __future__ import annotations

from coffee_shop import CoffeeShop, Position


def build_shop() -> CoffeeShop:
    """Кофейня бизнес-центра: меню и стоп-лист на текущий момент."""
    menu = [
        Position("Эспрессо", 150.0, 2, "coffee"),
        Position("Латте", 220.0, 4, "coffee"),
        Position("Капучино", 210.0, 4, "coffee"),
        Position("Зелёный чай", 120.0, 3, "tea"),
        Position("Апельсиновый сок", 180.0, 1, "juice"),
    ]
    return CoffeeShop(menu, stop_list=["Зелёный чай"])


def main() -> None:
    shop = build_shop()

    print("=== Меню, доступное к предзаказу ===")
    for position in shop.available_positions():
        print(f"{position.name:<18} {position.price:>7.2f} руб.  ~{position.prep_minutes} мин")

    print("\n=== Стоп-лист ===")
    print("Зелёный чай закончился. Замена:", ", ".join(shop.find_replacements("Зелёный чай")))

    order = shop.create_order(["Латте", "Эспрессо"])
    print(f"\n=== Заказ №{order.number} ===")
    for position in order.items:
        print(f"  {position.name:<18} {position.price:>7.2f} руб.")
    print(f"Итого: {shop.order_total(order.number):.2f} руб.")
    print(f"Статус: {order.status.value}")

    shop.start_preparing(order.number)
    print(f"\nБариста начал готовить -> сотрудник видит «{shop.readiness_message(order.number)}»")

    shop.mark_ready(order.number)
    print(f"Заказ готов. Статус: {order.status.value}")
    print(f"Заказов в очереди бариста: {len(shop.queue())}")


if __name__ == "__main__":
    main()
