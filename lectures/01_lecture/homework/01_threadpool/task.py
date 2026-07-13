"""
Домашнее задание 1: ThreadPoolExecutor 🧵

Вы пишете сервис, который собирает данные из нескольких внешних API.
Каждый запрос занимает ~50 мс (I/O-bound). Нужно использовать
пул потоков для ускорения.

Задания:
    1.1 — Базовый пул потоков
    1.2 — Обработка ошибок
    1.3 — Прогресс-бар (повышенная сложность)

📖 См. лекцию 1, раздел 3 (Threading) и примеры:
   lectures/01_lecture/examples/02_threading/01_simple_thread.py
   lectures/01_lecture/examples/02_threading/02_thread_pool.py
"""
from typing import Callable


# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ — не меняйте их
# ═══════════════════════════════════════════════════════════


def fetch_one(url: str) -> str:
    """Заглушка HTTP-запроса. 'Скачивает' URL за ~50 мс."""
    import time

    time.sleep(0.05)
    return f"data:{url}"


def fetch_one_with_delay(url_delay: tuple[str, float]) -> str:
    """Заглушка с кастомной задержкой: (url, delay) -> data."""
    url, delay = url_delay
    import time

    time.sleep(delay)
    return f"data:{url}"


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 1.1 — Базовый пул потоков
# ═══════════════════════════════════════════════════════════


def fetch_all(urls: list[str], max_workers: int = 4) -> list[str]:
    """Скачать все URL через ThreadPoolExecutor.

    Требования:
        - Использовать ThreadPoolExecutor как context manager
        - Результаты в том же порядке, что и urls
        - Не создавать потоки вручную

    Параметры:
        urls: список строк-URL
        max_workers: размер пула

    Пример:
        >>> fetch_all(["a", "b", "c"], max_workers=2)
        ['data:a', 'data:b', 'data:c']
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = pool.map(fetch_one, urls)
    return list(results)


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 1.2 — Обработка ошибок
# ═══════════════════════════════════════════════════════════


def fetch_all_with_errors(urls: list[str], max_workers: int = 4) -> list[str | None]:
    """Скачать URL, возвращая None для упавших.

    Некоторые URL могут вызывать исключение (например, ConnectionError).
    Нужно перехватить исключения и вернуть None для таких URL,
    не прерывая обработку остальных.

    Для имитации ошибок: если в URL есть подстрока "bad" — считать его
    проблемным и имитировать ошибку соединения.

    Требования:
        - Все URL должны быть обработаны (первая ошибка не прерывает)
        - Для "bad" URL вернуть None
        - Для остальных — результат fetch_one()
    """

    def fetch_one_except_bad(url: str) -> str | None:
        return None if "bad" in url else fetch_one(url)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = pool.map(fetch_one_except_bad, urls)
    return list(results)


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 1.3 — Прогресс-бар (повышенная сложность)
# ═══════════════════════════════════════════════════════════


def fetch_all_with_progress(
    urls: list[str],
    max_workers: int = 4,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[str]:
    """Скачать URL с уведомлением о прогрессе.

    После завершения каждого URL вызывать progress_callback(completed, total).
    Результаты вернуть в порядке завершения, а не в порядке urls.

    Параметры:
        urls: список URL
        max_workers: размер пула
        progress_callback: функция(completed, total)

    Требования:
        - progress_callback вызывается после каждого завершённого URL
        - Результаты в порядке завершения (as completed)

    Пример:
        completed = []
        def on_progress(done, total):
            completed.append(done)

        results = fetch_all_with_progress(
            ["a", "b", "c"], max_workers=2, progress_callback=on_progress
        )
        # completed[-1] == 3
    """

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future2url = {pool.submit(fetch_one, u): u for u in urls}
        url_res = dict()
        for future in as_completed(future2url):
            try:
                url_res[future2url[future]] = future.result()
            except Exception as exc:
                url_res[future2url[future]] = None
            finally:
                if progress_callback:
                    progress_callback(len(url_res), len(urls))
        return [url_res[u] for u in urls]