"""
01_bookstore — CRUD API для книжного магазина 📚

Спроектируйте REST API для управления каталогом книг.

Спецификация эндпоинтов (ничего не менять — тесты завязаны на них):

    GET    /books              — список книг (с опциональной фильтрацией)
    GET    /books/{id}         — одна книга по id
    POST   /books              — создать книгу
    PUT    /books/{id}         — полностью обновить книгу
    DELETE /books/{id}         — удалить книгу
    GET    /books/search       — поиск книг по названию или автору

    # Дополнительно — категории
    GET    /categories         — список категорий
    POST   /categories         — создать категорию

Требования к реализации:
    1. Используйте FastAPI + Pydantic
    2. Храните данные в памяти (глобальный список/словарь)
    3. Правильные HTTP-статусы:
        - 200 — успешный GET, PUT
        - 201 — успешный POST
        - 204 — успешный DELETE
        - 404 — ресурс не найден
        - 409 — конфликт (например, дубликат)
        - 422 — невалидные данные (Pydantic сам это делает)
    4. Валидация полей через Pydantic Field:
        - title:  не пустой, до 100 символов
        - author: не пустой, до 100 символов
        - year:   ≥ 0, до 2025
        - isbn:   строка 10 или 13 цифр (978-5-xxx...)
        - price:  > 0
        - category_id: опционально, ссылка на категорию
    5. Кастомная обработка ошибок:
        - BookNotFoundException → 404 c {"detail": "Book not found", "code": "NOT_FOUND"}
        - DuplicateIsbnException → 409 c {"detail": "...", "code": "DUPLICATE_ISBN"}
    6. Поиск /books/search?query=... — ищет по title и author (case-insensitive)
    7. Фильтрация GET /books?category_id=N&year=2024
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional

# ═══════════════════════════════════════════════════════════
# МОДЕЛИ
# ═══════════════════════════════════════════════════════════


class Category(BaseModel):
    """Доменная модель категории. Возвращается в ответах."""

    id: int
    name: str = Field(min_length=1, max_length=50)


class CategoryCreate(BaseModel):
    """Модель для создания категории (без id, лишние поля запрещены)."""

    name: str = Field(min_length=1, max_length=50)

    model_config = {"extra": "forbid"}


class Book(BaseModel):
    """Доменная модель книги. Возвращается в ответах GET/PUT."""

    id: int
    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1800, le=2025)
    isbn: str
    price: float = Field(gt=0)
    category_id: Optional[int] = None


class BookCreate(BaseModel):
    """Модель для создания/обновления книги (без id — сервер сгенерирует)."""

    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1800, le=2025)
    isbn: str
    price: float = Field(gt=0)
    category_id: Optional[int] = None


# ═══════════════════════════════════════════════════════════
# ИСКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════


class BookNotFoundException(HTTPException):
    """404 — книга не найдена."""

    def __init__(self):
        super().__init__(status_code=404,
                         detail={"detail": "Book not found", "code": "NOT_FOUND"})


class DuplicateIsbnException(HTTPException):
    """409 — ISBN уже существует."""

    def __init__(self):
        super().__init__(status_code=409,
                         detail={"detail": "...", "code": "DUPLICATE_ISBN"})



# ═══════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════

app = FastAPI(title="Bookstore API")

@app.exception_handler(BookNotFoundException)
def book_not_found_exception_handler(request: Request, exc: BookNotFoundException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)

@app.exception_handler(DuplicateIsbnException)
def duplicate_isbn_exception_handler(request: Request, exc: DuplicateIsbnException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)

# Хранилище
BOOKS: list[Book | None] = []
ISBNS: set[str] = set()
CATEGORIES: list[Category] = []


# ═══════════════════════════════════════════════════════════
# КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════


@app.get("/categories")
def list_categories():
    """GET /categories — список всех категорий."""
    return CATEGORIES  # [Category(**e) for e in CATEGORIES]


@app.post("/categories", status_code=201)
def create_category(category: CategoryCreate):
    """POST /categories — создать категорию."""
    CATEGORIES.append(Category(id=len(CATEGORIES), name=category.name))
    return CATEGORIES[-1]


# ═══════════════════════════════════════════════════════════
# CRUID КНИГ
# ═══════════════════════════════════════════════════════════


@app.get("/books")
def list_books(category_id: Optional[int] = None, year: Optional[int] = None):
    """GET /books — список книг. Опциональная фильтрация по category_id и year."""

    def check(book: Book | None) -> bool:
        return all([book is not None,
                    category_id is None or book.category_id == category_id,
                    year is None or book.year == year])

    return list(filter(check, BOOKS))


@app.get("/books/search")
def search_books(query: str):
    """GET /books/search?query=... — поиск по title и author (case-insensitive)."""
    return [book for book in BOOKS if book and (
            query.lower() in book.title.lower() or query.lower() in book.author.lower())]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    """GET /books/{id} — одна книга."""
    if 0 > book_id or book_id >= len(BOOKS) or not BOOKS[book_id]:
        raise BookNotFoundException
    return BOOKS[book_id]


@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    """POST /books — создать книгу.

    Проверять уникальность ISBN. Если дубликат — DuplicateIsbnException.
    """
    if book.isbn in ISBNS:
        raise DuplicateIsbnException()
    ISBNS.add(book.isbn)
    BOOKS.append(Book(id=len(BOOKS), **book.model_dump()))
    return BOOKS[-1]


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookCreate):
    """PUT /books/{id} — полностью обновить книгу."""
    if 0 > book_id or book_id >= len(BOOKS) or not BOOKS[book_id]:
        raise BookNotFoundException()
    ISBNS.remove(BOOKS[book_id].isbn)
    ISBNS.add(book.isbn)
    BOOKS[book_id] = Book(id=book_id, **book.model_dump())
    return BOOKS[book_id]


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """DELETE /books/{id} — удалить книгу."""
    if 0 > book_id or book_id >= len(BOOKS) or not BOOKS[book_id]:
        raise BookNotFoundException()
    ISBNS.remove(BOOKS[book_id].isbn)
    BOOKS[book_id] = None
