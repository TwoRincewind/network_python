"""
Домашнее задание 2: Race Condition и Lock 🔒

Несколько потоков одновременно изменяют общий счётчик.
Без синхронизации данные портятся из-за гонки (race condition).

Задания:
    2.1 — Увидеть race condition (запустить и наблюдать)
    2.2 — Исправить через Lock
    2.3 — Реализовать потокобезопасный банковский счёт

📖 См. лекцию 1, раздел 3 (Threading) и пример:
   lectures/01_lecture/examples/02_threading/02_thread_pool.py
   (Часть 3 Race condition — показана гонка и Lock)
"""

import threading


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 2.1 — Имитация гонки
# ═══════════════════════════════════════════════════════════


def increment_with_race(counter: list[int], times: int) -> None:
    """Увеличить counter[0] на times, НО с гонкой.

    Два потока, одновременно вызывающие эту функцию, должны
    приходить к некорректному результату (меньше 2 * times).

    Для воспроизведения гонки: читаем счётчик, делаем микро-паузу
    (time.sleep(0.000001)), потом записываем новое значение —
    между чтением и записью другой поток может успеть прочитать
    то же значение.

    Требования:
        - Не использовать Lock
        - Содержать искусственную задержку между чтением и записью
    """
    import time
    for _ in range(times):
        tmp = counter[0]
        time.sleep(0.000001)
        counter[0] = tmp + 1


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 2.2 — Исправление через Lock
# ═══════════════════════════════════════════════════════════


def increment_safe(counter: list[int], times: int, lock: threading.Lock) -> None:
    """Увеличить counter[0] на times, БЕЗ гонки.

    То же самое, что increment_with_race, но с Lock.
    Захватывайте lock перед чтением/записью counter[0].

    Требования:
        - Критическая секция должна быть минимальной
          (только чтение + запись, не весь цикл)
    """
    import time
    for _ in range(times):
        lock.acquire()
        tmp = counter[0]
        time.sleep(0.000001)
        counter[0] = tmp + 1
        lock.release()


# ═══════════════════════════════════════════════════════════
# ЗАДАНИЕ 2.3 — Банковский счёт (повышенная сложность)
# ═══════════════════════════════════════════════════════════


class InsufficientFundsError(Exception):
    """Исключение: недостаточно средств на счёте."""

    pass


class BankAccount:
    """Потокобезопасный банковский счёт.

    Методы должны быть безопасны при вызове из нескольких потоков.

    Требования:
        - deposit(amount): добавить к балансу, amount > 0
        - withdraw(amount): списать, если хватает средств.
          Если не хватает — raise InsufficientFundsError.
          Баланс не должен уйти в минус.
        - get_balance(): вернуть текущий баланс
        - Все операции потокобезопасны

    Пример:
        acc = BankAccount()
        acc.deposit(100)       # баланс: 100
        acc.withdraw(50)       # баланс: 50
        acc.withdraw(100)      # InsufficientFundsError, баланс: 50
        acc.get_balance()      # 50
    """

    def __init__(self, initial_balance: float = 0.0) -> None:
        self.balance = initial_balance
        self.lock = threading.Lock()

    def deposit(self, amount: float) -> None:
        self.lock.acquire()
        self.balance += amount
        self.lock.release()

    def withdraw(self, amount: float) -> None:
        self.lock.acquire()
        if self.balance < amount:
            self.lock.release()
            raise InsufficientFundsError()
        self.balance -= amount
        self.lock.release()

    def get_balance(self) -> float:
        return self.balance