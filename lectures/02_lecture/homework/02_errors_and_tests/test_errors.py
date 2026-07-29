"""Тесты к ДЗ 2: Error handling и тестирование."""
import sys
import os
from string import ascii_letters as letters
from random import choice
from threading import Thread

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


class TestGetItems:
    def test_get_all(self):
        names = "Alpha_Beta gamma_Delta".split('_')
        for name in names:
            client.post("/items", json={"name": name})
        resp = client.get("/items")
        assert resp.status_code == 200
        assert "items" in resp.json()
        assert isinstance(resp.json()["items"], list)
        items_names = [item["name"] for item in resp.json()["items"]]
        assert all(name in items_names for name in names)


class TestCounter:
    def test_checks_item(self):
        assert client.get("/items/42/counter").status_code == 404

    def test_increases(self):
        item_id = TestCounter._ensure_enough_items(1)[0]
        start_value = TestCounter._get(item_id)
        for i in range(start_value + 1, start_value + 10):
            assert TestCounter._get(item_id) == i

    def test_race_condition(self):
        """straight bullshit because server processes one at a time"""

        def work(item_id: int, requests_cnt: int):
            for i in range(requests_cnt):
                TestCounter._get(item_id)

        items_cnt = 4
        item_ids = TestCounter._ensure_enough_items(items_cnt)
        mult = 400
        request_cnts = list(range(mult, (items_cnt + 1) * mult, mult))

        start_value = TestCounter._get(item_ids[0])
        ts = [Thread(target=work, args=args) for args in zip(item_ids, request_cnts)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        finish_value = TestCounter._get(item_ids[0])
        assert finish_value - start_value == sum(request_cnts) + 1

    @staticmethod
    def _get(item_id: int) -> int:
        return client.get(f"/items/{item_id}/counter").json()["counter"]

    @staticmethod
    def _ensure_enough_items(items_needed: int) -> list[int]:
        resp = client.get("/items")
        assert resp.status_code == 200
        item_ids = [item["id"] for item in resp.json()["items"]]
        for i in range(len(item_ids), items_needed):
            item = {"name": ''.join(choice(letters) for _ in range(10))}
            item_ids.append(client.post("/items", json=item).json()["id"])
        return item_ids


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


class TestSlowASync:
    def test_slow_async_returns_correctly(self):
        resp = client.get("/slow-async")
        assert resp.status_code == 200
        assert resp.json() == {"status": "done"}

    def test_slow_async_is_async(self):
        """Проверяем, что /slow-async не блокирует другие запросы."""
        import threading
        import time

        results = []

        def call_slow():
            t0 = time.perf_counter()
            resp = client.get("/slow-async")
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
            f"fast запрос занял {fast_time:.4f}s — "
            f"похоже slow-async блокирует event loop!"
        )
        assert 0.4 < slow_time < 1.0, (
            f"slow-async должен быть ~0.5s, получили {slow_time:.2f}s"
        )


class TestSlowSync:
    def test_slow_sync_returns_correctly(self):
        resp = client.get("/slow-sync")
        assert resp.status_code == 200
        assert resp.json() == {"status": "done"}

    def test_slow_sync_is_sync(self):
        """Проверяем, что /slow-sync блокирует другие запросы."""
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

        assert fast_time > 0.2, (
            f"fast запрос занял {fast_time:.4f}s — "
            f"похоже slow-sync не блокирует event loop"
        )
        assert 0.4 < slow_time < 1, (
            f"slow-sync должен быть ~0.5s, получили {slow_time:.2f}s"
        )


class TestErrorResponseFormat:
    def test_error_has_detail(self):
        resp = client.get("/items/999999")
        data = resp.json()
        assert "detail" in data, "Ответ об ошибке должен содержать detail"
        assert isinstance(data["detail"], str)
