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
import asyncio

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


@app.get("/items/{item_id}/counter")
def get_counter(item_id: int):
    # TODO:
    global COUNTER
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
    try:
        ITEMS.pop(item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")


@app.get("/divide")
def divide(a: int, b: int):
    try:
        return {"result": a / b}
    except ZeroDivisionError:
        raise HTTPException(status_code=400, detail="Divide by zero")


@app.get("/slow-sync")
async def slow_sync():
    await asyncio.sleep(1)
    return {"status": "done"}
