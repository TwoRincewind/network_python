"""
02_errors_and_tests — чиним и тестируем 🛠️

В app.py лежит сломанное FastAPI-приложение. Найдите и исправьте ВСЕ проблемы.

Задача А: Исправить приложение (task.py)
    Скопируйте app.py сюда и исправьте все ошибки.
    Внимание: tests будут проверять ВАШУ реализацию, не оригинальный app.py.

    Чего ждут тесты:
        ✓ POST /items → 201 Created
        ✓ GET  /items/{id} → 200 или 404
        ✓ PUT  /items/{id} → 200 или 404
        ✓ DELETE /items/{id} → 204 или 404
        ✓ GET  /divide?a=10&b=0 → 400 (не 500!)
        ✓ GET  /items/{id}/counter → race condition отсутствует
        ✓ GET  /slow-sync → async def + await asyncio.sleep
        ✓ DELETE возвращает правильный статус (204)

Задача Б: Написать тесты в test_errors.py
    Покрыть все эндпоинты.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from threading import Lock

app = FastAPI()

ITEMS: dict[int, dict] = {}
NEXT_ID = 1
COUNTER = 0


class ItemCreate(BaseModel):
    name: str


class ItemUpdate(BaseModel):
    name: str = ""


# ═══════════════════════════════════════════════════════════
# ИСПРАВЛЯЙТЕ НИЖЕ
# ═══════════════════════════════════════════════════════════


@app.get("/items", status_code=200)
def list_items():
    return {"items": list(ITEMS.values())}


@app.get("/items/{item_id}", status_code=200)
def get_item(item_id: int):
    try:
        return ITEMS[item_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    global NEXT_ID
    ITEMS[NEXT_ID] = {"id": NEXT_ID} | item.model_dump()
    NEXT_ID += 1
    return ITEMS[NEXT_ID - 1]


COUNTER_LOCK = Lock()


@app.get("/items/{item_id}/counter")
def get_counter(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(404, detail="Item not found")
    global COUNTER
    with COUNTER_LOCK:
        COUNTER += 1
        return {"counter": COUNTER}


@app.put("/items/{item_id}", status_code=200)
def update_item(item_id: int, update: ItemUpdate):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS[item_id] = {"id": item_id} | update.model_dump()
    return ITEMS[item_id]


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS.pop(item_id)


@app.get("/divide")
def divide(a: int, b: int):
    if b == 0:
        raise HTTPException(status_code=400, detail="Divide by zero")
    return {"result": a / b}


@app.get("/slow-sync")
def slow_sync():
    from time import perf_counter #, sleep
    # sleep(0.5)
    t0 = perf_counter()
    while perf_counter() - t0 < 0.5:
        t0 = t0
    return {"status": "done"}


@app.get("/slow-async")
async def slow_async():
    from asyncio import sleep
    await sleep(0.5)
    return {"status": "done"}
