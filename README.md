# CF-01 «Предзаказ кофе» — CI и модульное тестирование

Учебный проект по лабораторной работе «Непрерывная интеграция (CI) и модульное
тестирование». Предметная область — сервис предзаказа кофе для сотрудников
бизнес-центра (ТЗ `TZ-CF-01-v1.0`).

## Зачем это нужно бизнесу

40 сотрудников, перерыв 15 минут, фактическое ожидание до 9 минут, 2–3 заказа
из 10 теряются в общем чате. Сервис предзаказа должен убрать очередь:
10 оформленных заказов за перерыв без звонков и уточнений.

## Структура проекта

```
coffee-preorder-ci/
├── .github/workflows/ci.yml   # CI-конвейер GitHub Actions
├── coffee_shop.py             # доменная логика предзаказа
├── test_coffee_shop.py        # модульные тесты (pytest)
├── demo.py                    # демонстрационный сценарий
├── requirements.txt           # зависимости проекта
└── README.md
```

## Что реализовано (трассировка на требования ТЗ)

| Требование | Где в коде | Тесты |
|---|---|---|
| FR-01 Предзаказ из меню | `CoffeeShop.create_order`, `add_item`, `menu_positions` | `test_create_order_from_menu`, `test_menu_contains_all_positions` |
| FR-02 Время готовности | `readiness_message`, `start_preparing`, `mark_ready` | `test_readiness_message_while_preparing`, `test_readiness_message_is_none_after_ready` |
| FR-03 Отмена до приготовления | `cancel_order` | `test_cancel_accepted_order`, `test_cancel_after_preparing_is_rejected` |
| FR-04 Стоп-лист и замена | `available_positions`, `find_replacements`, `stop_position` | `test_available_positions_exclude_stop_list`, `test_unavailable_position_offers_replacements` |
| FR-06 Лимит 3 позиции в заказе | `add_item`, `create_order` | `test_order_limit_allows_three_positions`, `test_order_limit_rejects_fourth_position` |
| Цена заказа | `order_total` | `test_order_total_sums_every_position` |

## Локальный запуск

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

pytest test_coffee_shop.py -v
pytest test_coffee_shop.py --cov=coffee_shop --cov-report=term-missing
mypy coffee_shop.py
python demo.py
```

## CI-конвейер

`.github/workflows/ci.yml` запускается на каждый `push` и `pull_request` в ветку
`main` и выполняет четыре шага:

1. выгрузка кода (`actions/checkout@v4`);
2. установка Python из матрицы версий (`3.10`, `3.11`, `3.12`) и зависимостей;
3. статическая проверка типов `mypy coffee_shop.py`;
4. модульные тесты `pytest` с отчётом о покрытии.

«Зелёная» сборка означает, что все четыре шага прошли на всех версиях Python.
