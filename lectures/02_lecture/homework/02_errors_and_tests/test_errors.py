"""Тесты к ДЗ 2: Error handling и тестирование."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from starlette.testclient import TestClient

from task import app

client = TestClient(app)


class TestCreateItem:
    def test_create_returns_201(self):
        resp = client.post("/items", json={"name": "Новый"})
        assert resp.status_code == 201

    def test_create_returns_id(self):
        resp = client.post("/items", json={"name": "Тест"})
        data = resp.json()
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_extra_field_ignored(self):
        """ItemCreate не должен reject'ить лишние поля (extra='ignore' по умолчанию у pydantic)."""
        resp = client.post("/items", json={"name": "OK", "extra": "ignored"})
        assert resp.status_code == 201

    def test_create_missing_name(self):
        resp = client.post("/items", json={})
        assert resp.status_code == 422


class TestGetItem:
    def test_get_existing(self):
        created = client.post("/items", json={"name": "Для поиска"}).json()
        item_id = created["id"]
        resp = client.get(f"/items/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Для поиска"

    def test_get_not_found(self):
        resp = client.get("/items/999999")
        assert resp.status_code == 404

    def test_content_type(self):
        resp = client.get("/items/1")
        assert "application/json" in resp.headers["content-type"]


class TestUpdateItem:
    def test_update_existing(self):
        created = client.post("/items", json={"name": "Старое"}).json()
        item_id = created["id"]
        resp = client.put(f"/items/{item_id}", json={"name": "Новое"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Новое"

    def test_update_not_found(self):
        resp = client.put("/items/999999", json={"name": "X"})
        assert resp.status_code == 404

    def test_update_preserves_id(self):
        created = client.post("/items", json={"name": "A"}).json()
        item_id = created["id"]
        updated = client.put(f"/items/{item_id}", json={"name": "B"}).json()
        assert updated["id"] == item_id


class TestDeleteItem:
    def test_delete_returns_204(self):
        created = client.post("/items", json={"name": "Удалить"}).json()
        item_id = created["id"]
        resp = client.delete(f"/items/{item_id}")
        assert resp.status_code == 204
        assert resp.text == ""  # 204 — пустое тело

    def test_delete_actually_removes(self):
        created = client.post("/items", json={"name": "Исчезнуть"}).json()
        item_id = created["id"]
        client.delete(f"/items/{item_id}")
        resp = client.get(f"/items/{item_id}")
        assert resp.status_code == 404

    def test_delete_not_found(self):
        resp = client.delete("/items/999999")
        assert resp.status_code == 404

    def test_delete_twice(self):
        created = client.post("/items", json={"name": "Дважды"}).json()
        item_id = created["id"]
        client.delete(f"/items/{item_id}")
        resp = client.delete(f"/items/{item_id}")
        assert resp.status_code == 404

    def test_ids_dont_shift_after_delete(self):
        """После удаления id не должны съезжать."""
        id1 = client.post("/items", json={"name": "A"}).json()["id"]
        id2 = client.post("/items", json={"name": "B"}).json()["id"]
        client.delete(f"/items/{id1}")
        resp = client.get(f"/items/{id2}")
        assert resp.status_code == 200
        assert resp.json()["id"] == id2


class TestDivide:
    def test_divide_ok(self):
        resp = client.get("/divide", params={"a": 10, "b": 2})
        assert resp.status_code == 200
        assert resp.json() == {"result": 5.0}

    def test_divide_by_zero(self):
        """Деление на ноль → 400, не 500."""
        resp = client.get("/divide", params={"a": 10, "b": 0})
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data

    def test_divide_missing_params(self):
        resp = client.get("/divide")
        assert resp.status_code == 422


class TestSlowSync:
    def test_slow_sync_returns_correctly(self):
        resp = client.get("/slow-sync")
        assert resp.status_code == 200
        assert resp.json() == {"status": "done"}

    def test_slow_sync_is_async(self):
        """Проверяем, что /slow-sync не блокирует другие запросы."""
        import threading
        import time

        results = []

        def call_slow():
            t0 = time.perf_counter()
            resp = client.get("/slow-sync")
            elapsed = time.perf_counter() - t0
            results.append(("slow", elapsed, resp.status_code))

        def call_fast():
            time.sleep(0.1)  # стартуем чуть позже
            t0 = time.perf_counter()
            resp = client.get("/items")
            elapsed = time.perf_counter() - t0
            results.append(("fast", elapsed, resp.status_code))

        t1 = threading.Thread(target=call_slow)
        t2 = threading.Thread(target=call_fast)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        slow_time = next(r[1] for r in results if r[0] == "slow")
        fast_time = next(r[1] for r in results if r[0] == "fast")

        # Если бы slow блокировал event loop — fast бы ждал
        assert fast_time < 0.2, (
            f"fast запрос занял {fast_time:.2f}s — "
            f"похоже slow-sync блокирует event loop!"
        )
        assert 0.4 < slow_time < 1.0, (
            f"slow-sync должен быть ~0.5s, получили {slow_time:.2f}s"
        )


class TestErrorResponseFormat:
    def test_error_has_detail(self):
        resp = client.get("/items/999999")
        data = resp.json()
        assert "detail" in data, "Ответ об ошибке должен содержать detail"
        assert isinstance(data["detail"], str)
