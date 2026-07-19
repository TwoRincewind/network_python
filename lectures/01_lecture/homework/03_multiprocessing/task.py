"""
Домашнее задание 3: Multiprocessing ⚡

У вас есть числа, для каждого нужно вычислить сложную функцию (CPU-bound).
Через потоки не ускорить — GIL мешает. Нужно распараллелить через
multiprocessing.Pool.

Задания:
    3.1 — Распараллелить вычисление через Pool
    3.2 — Сравнить производительность threading vs multiprocessing

📖 См. лекцию 1, раздел 4 (Multiprocessing) и пример:
   lectures/01_lecture/examples/03_multiprocessing/02_cpu_bound.py
"""


# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ — не меняйте их
# ═══════════════════════════════════════════════════════════


def is_prime(n: int) -> bool:
    """Проверка числа на простоту (CPU-bound)."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def heavy_compute(x: int) -> int:
    """'Тяжёлая' функция: сумма простых чисел до x."""
    total = 0
    for n in range(2, x + 1):
        if is_prime(n):
            total += n
    return total


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 3.1 — Пул процессов
# ═══════════════════════════════════════════════════════════


def compute_sequential(numbers: list[int]) -> list[int]:
    """Вычислить heavy_compute для каждого числа ПОСЛЕДОВАТЕЛЬНО.

    Просто для сравнения с параллельной версией.
    """
    return [heavy_compute(n) for n in numbers]


def compute_parallel_pool(numbers: list[int], processes: int = 4) -> list[int]:
    """Вычислить heavy_compute через multiprocessing.Pool.

    Требования:
        - Использовать Pool(processes) как context manager
        - Результаты в порядке numbers
    """
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=processes) as pool:
        return list(pool.map(heavy_compute, numbers))


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 3.2 — ThreadPool vs Pool (сравнение)
# ═══════════════════════════════════════════════════════════


def compute_with_threads(numbers: list[int], workers: int = 4) -> list[int]:
    """Вычислить heavy_compute через ThreadPoolExecutor.

    Должно работать МЕДЛЕННЕЕ, чем Pool, из-за GIL.
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(heavy_compute, numbers))
