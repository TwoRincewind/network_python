"""
Домашнее задание 4: Asyncio 🔄

Контекст: нужно обработать 1000 входящих HTTP-запросов.
ThreadPoolExecutor создаёт 1000 потоков — слишком много памяти.
Asyncio позволяет держать тысячи соединений в одном потоке.

Задания:
    4.1 — Базовый async/await (asyncio.sleep)
    4.2 — Параллельный запуск через asyncio.gather
    4.3 — Групповой запуск с asyncio.TaskGroup
    4.4 — Таймауты через asyncio.wait_for
    4.5 — Отмена задач (CancelledError)
    4.6 — Результаты по мере готовности (asyncio.as_completed)
    4.7 — Смешивание sync и async (asyncio.to_thread) [повышенная сложность]

📖 См. лекцию 1, раздел 5 (Asyncio) и примеры:
   lectures/01_lecture/examples/04_asyncio/01_task_group.py
   lectures/01_lecture/examples/04_asyncio/02_timeouts.py
   lectures/01_lecture/examples/04_asyncio/03_cancelation.py
   lectures/01_lecture/examples/04_asyncio/04_as_completed.py
"""

import asyncio
from asyncio import CancelledError


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.1 — Первая корутина
# ═══════════════════════════════════════════════════════════


async def fetch_one_async(url: str) -> str:
    """Асинхронно 'скачать' URL.

    Вместо time.sleep() используйте await asyncio.sleep().

    Требования:
        - Функция объявлена через async def
        - Возвращает f"data:{url}"
    """
    await asyncio.sleep(0.01)
    return f"data:{url}"


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.2 — Параллельный запуск
# ═══════════════════════════════════════════════════════════


async def fetch_all_async(urls: list[str]) -> list[str]:
    """Скачать все URL конкурентно через asyncio.gather.

    Требования:
        - Запустить fetch_one_async для каждого URL конкурентно
        - Вернуть результаты в порядке urls
    """
    return await asyncio.gather(*[fetch_one_async(url) for url in urls])


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.3 — Групповой запуск (TaskGroup)
# ═══════════════════════════════════════════════════════════

# Вспомогательная функция — не менять


async def fetch_with_delay(name: str, delay: float, fail: bool = False) -> str:
    """Имитация асинхронной загрузки.

    Параметры:
        name: имя загрузки
        delay: время задержки в секундах
        fail: если True — выбросить ValueError

    НЕ МЕНЯТЬ.
    """
    await asyncio.sleep(delay)
    if fail:
        raise ValueError(f"Ошибка загрузки {name}")
    return f"data:{name}"


async def run_task_group(names: list[str]) -> dict[str, str | None]:
    """Запустить группу загрузок через asyncio.TaskGroup.

    Для каждого имени нужно создать задачу через TaskGroup,
    вызвав fetch_with_delay(name, delay=0.1, fail=("bad" in name)).

    Требования:
        - Использовать async with asyncio.TaskGroup() как контекстный менеджер
        - Если какая-то задача упала с исключением — нужно перехватить
          все ошибки через except* ValueError
        - Вернуть словарь {name: result}, где result — строка для успешных
          и None для упавших задач
        - Если все задачи упали — вернуть пустой словарь
    """
    name = dict()
    try:
        async with asyncio.TaskGroup() as tg:
            for s in names:
                t = tg.create_task(fetch_with_delay(s, 0.1, "bad" in s))
                name[t] = s
    except* ValueError as excgroup:
        pass
    for t, s in name.items():
        print(s, t.done(), t.cancelled(), t.exception())
    ret = {s: t.result() for t, s in name.items() if t.done() and not t.cancelled() and not t.exception()}
    if ret:
        for s in names:
            if not s in ret:
                ret[s] = None
    return ret


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.4 — Таймауты
# ═══════════════════════════════════════════════════════════


async def fetch_with_timeout(url: str, delay: float, timeout: float) -> str:
    """Скачать URL с таймаутом.

    Используйте asyncio.wait_for(), чтобы ограничить время ожидания.

    Требования:
        - Вызвать fetch_one_async(url) с таймаутом timeout секунд
        - Если не уложились — выбросить TimeoutError
        - Если успели — вернуть результат fetch_one_async(url)
    """
    # а зачем мне делэй если не передаю дальше? странные указания, из-за них и тесты не проходят дальше
    return await asyncio.wait_for(fetch_with_delay(url, delay), timeout)


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.5 — Отмена задач
# ═══════════════════════════════════════════════════════════


async def cancellable_worker(name: str, steps: int) -> str:
    """Корутина, которую можно отменить.

    Имитирует долгую работу: на каждом шаге делает
    await asyncio.sleep(0.1) и печатает шаг.

    Требования:
        - При получении CancelledError напечатать
          f"  {name}: очищаю ресурсы..." и пробросить исключение ДАЛЬШЕ (raise)
        - Если не отменили — вернуть f"{name}: готов после {steps} шагов"
    """
    try:
        for i in range(steps):
            await asyncio.sleep(0.1)
            print(f"{i}")
        return f"{name}: готов после {steps} шагов"
    except CancelledError as e:
        print(f"{name}: очищаю ресурсы...")
        raise e


async def run_with_cancel(name: str, steps: int, cancel_after: float) -> str | None:
    """Запустить cancellable_worker и отменить через cancel_after секунд.

    Требования:
        - Создать задачу через asyncio.create_task()
        - Подождать cancel_after секунд через asyncio.sleep()
        - Отменить задачу через task.cancel()
        - Попробовать получить результат через await task
        - Если поймали CancelledError — вернуть None
        - Если задача успела завершиться — вернуть результат
    """
    task = asyncio.create_task(cancellable_worker(name, steps))
    await asyncio.sleep(cancel_after)
    task.cancel()
    try:
        return await task
    except CancelledError:
        return


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.6 — Асинхронный as_completed
# ═══════════════════════════════════════════════════════════


async def fast_or_slow(name: str, delay: float) -> str:
    """Имитация быстрой или медленной загрузки.

    НЕ МЕНЯТЬ.
    """
    await asyncio.sleep(delay)
    return f"{name}: готов за {delay}с"


async def fetch_as_completed(tasks: list[tuple[str, float]]) -> list[str]:
    """Запустить загрузки и вернуть результаты по мере готовности.

    Параметры:
        tasks: список кортежей (name, delay)

    Требования:
        - Создать список корутин из fast_or_slow для каждого (name, delay)
        - Использовать asyncio.as_completed() для обхода результатов
        - Вернуть список строк в порядке ЗАВЕРШЕНИЯ, а не в порядке запуска
    """
    coros = [fast_or_slow(name, delay) for name, delay in tasks]
    return [await t for t in asyncio.as_completed(coros)]


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 4.7 — Смешивание sync и async (повышенная сложность)
# ═══════════════════════════════════════════════════════════


def blocking_compute(x: int) -> int:
    """CPU-bound функция: проверка на простоту.

    НЕ МЕНЯТЬ. Это синхронная блокирующая функция.
    """
    import math
    import time

    time.sleep(0.01)  # имитация тяжёлого вычисления
    for i in range(2, int(math.sqrt(x)) + 1):
        if x % i == 0:
            return 0
    return x  # простое число


async def async_process_numbers(numbers: list[int], max_workers: int = 4) -> list[int]:
    """Обработать числа, выгружая CPU-bound код в пул потоков.

    blocking_compute — блокирующая функция. Её нельзя вызывать
    напрямую в корутине — она заблокирует весь event loop.
    Нужно выгрузить её в отдельный поток через asyncio.to_thread().

    Требования:
        - Не блокировать event loop — выгрузить blocking_compute в пул потоков
        - Использовать asyncio.to_thread() или loop.run_in_executor()
        - max_workers: размер пула потоков
        - Результаты в порядке numbers
    """
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        def f(num: int):
            return asyncio.get_running_loop().run_in_executor(pool, blocking_compute, num)
        return await asyncio.gather(*map(f, numbers))
