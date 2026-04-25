# Experimental Booking Stand (FastAPI)

Минимальный backend-стенд для сравнения двух архитектурных режимов обработки операции бронирования помещения:
- `centralized_sync` — вся цепочка синхронно в рамках запроса;
- `hybrid_async` — критическая часть синхронно, вторичные шаги через in-memory очередь и worker.

## Назначение

Стенд предназначен для исследовательского прототипирования в рамках ВКР по анализу архитектурных решений системы управления ресурсами малого предприятия креативной индустрии.

## Технологии

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- SQLite
- Pydantic
- Uvicorn
- asyncio.Queue
- httpx

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## Запуск API

```bash
uvicorn app.main:app --reload
```

API будет доступен на `http://127.0.0.1:8000`.

## Worker

Worker запускается вместе с API в фоне (lifespan FastAPI).

Управление worker через API:
- `POST /experiments/worker/on` — включить обработку очереди;
- `POST /experiments/worker/off` — выключить обработку очереди;
- `POST /experiments/worker/delay` с `{"delay_ms": 200}` — задать искусственную задержку.

## Основные эндпоинты

- `POST /experiments/reset`
- `POST /experiments/seed`
- `GET /rooms`
- `GET /bookings`
- `POST /bookings`
- `GET /experiments/metrics`
- `POST /experiments/worker/on`
- `POST /experiments/worker/off`
- `POST /experiments/worker/delay`

## Переключение архитектурного режима

Режим выбирается в `POST /bookings` через поле `mode`:
- `centralized_sync`
- `hybrid_async`

Пример:

```json
{
  "room_id": 1,
  "user_id": 1,
  "start_time": "2026-04-20T10:00:00",
  "end_time": "2026-04-20T11:00:00",
  "mode": "hybrid_async",
  "scenario": "manual"
}
```

## Конфликт бронирования

Для одной комнаты запрещены пересекающиеся интервалы.
При конфликте API возвращает `HTTP 409`, а событие фиксируется в `MetricsEvent`.

## Какие метрики собираются

`MetricsEvent` для каждого запроса бронирования:
- `request_id`
- `scenario`
- `mode`
- `started_at`
- `finished_at`
- `duration_ms`
- `result` (`success/conflict/error`)
- `notes`

Также worker логирует выполнение асинхронных задач в `MetricsEvent` с `scenario=worker`.

## Нагрузочный скрипт

Скрипт: `load/compare_modes.py`

Что делает:
1. Сбрасывает данные и seed'ит тестовые сущности.
2. Прогоняет оба режима (`centralized_sync`, `hybrid_async`).
3. Выполняет:
   - Сценарий A: 20 последовательных неконфликтующих запросов.
   - Сценарий B: 20 параллельных запросов с конфликтами.
4. Сохраняет агрегированные итоги в CSV (`results.csv` по умолчанию).

Запуск:

```bash
python load/compare_modes.py --output results.csv --worker-delay-ms 100
```

Колонки CSV:
- `mode`
- `total_requests`
- `success_count`
- `conflict_count`
- `avg_response_ms`
- `max_response_ms`
