from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, create_engine, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

app = FastAPI()

# -----------------------------
# CORS setup
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# MySQL connection
# -----------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Ankit261")
DB_NAME = os.getenv("DB_NAME", "library_db")

DATABASE_URL = f"mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------
# Models
# -----------------------------
class BookModel(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    category = Column(String(255))
    available = Column(Boolean, default=True)
    quantity = Column(Integer, default=1)

class BorrowedBookModel(Base):
    __tablename__ = "borrowed_books"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    borrow_date = Column(TIMESTAMP, server_default=func.now())
    return_date = Column(TIMESTAMP, nullable=True)

class BorrowSummaryModel(Base):
    __tablename__ = "borrow_summary"
    user_id = Column(Integer, primary_key=True, index=True)
    borrow_count = Column(Integer, default=0)

# ✅ NEW: Users table model (to join with summary)
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255))
    role = Column(String(50))

Base.metadata.create_all(bind=engine)

# -----------------------------
# Schemas
# -----------------------------
class Book(BaseModel):
    id: int
    title: str
    author: str
    category: str
    available: bool = True
    quantity: int = 1
    class Config:
        orm_mode = True

class BookList(BaseModel):
    books: List[Book]

class BorrowedBook(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrow_date: datetime
    return_date: Optional[datetime]
    class Config:
        orm_mode = True

class BorrowSummary(BaseModel):
    user_id: int
    borrow_count: int
    class Config:
        orm_mode = True

# ✅ NEW: Enriched summary schema
class BorrowSummaryOut(BaseModel):
    user_id: int
    name: Optional[str]
    email: Optional[str]
    role: Optional[str]
    borrow_count: int
    class Config:
        orm_mode = True

# -----------------------------
# Dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# Endpoints
# -----------------------------
@app.get("/books", response_model=List[Book])
def list_books(db: Session = Depends(get_db)):
    books = db.query(BookModel).all()
    for b in books:
        b.available = b.quantity > 0
    return books

@app.post("/books", response_model=Book)
def add_book(book: Book, db: Session = Depends(get_db)):
    existing = db.query(BookModel).filter(BookModel.id == book.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Book with ID {book.id} already exists")
    db_book = BookModel(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.post("/books/bulk", response_model=List[Book])
def add_multiple_books(book_list: BookList, db: Session = Depends(get_db)):
    added_books = []
    for book in book_list.books:
        existing = db.query(BookModel).filter(BookModel.id == book.id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Book with ID {book.id} already exists")
        db_book = BookModel(**book.dict())
        db.add(db_book)
        added_books.append(db_book)
    db.commit()
    for b in added_books:
        db.refresh(b)
    return added_books

@app.post("/books/{book_id}/borrow", response_model=BorrowedBook)
def borrow_book(book_id: int, user_id: int, db: Session = Depends(get_db)):
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.quantity <= 0:
        raise HTTPException(status_code=400, detail="No copies available")

    book.quantity -= 1
    book.available = book.quantity > 0
    db.commit()

    borrow_record = BorrowedBookModel(user_id=user_id, book_id=book_id)
    db.add(borrow_record)

    summary = db.query(BorrowSummaryModel).filter(BorrowSummaryModel.user_id == user_id).first()
    if summary:
        summary.borrow_count += 1
    else:
        summary = BorrowSummaryModel(user_id=user_id, borrow_count=1)
        db.add(summary)

    db.commit()
    db.refresh(borrow_record)
    return borrow_record

@app.post("/books/{book_id}/return", response_model=BorrowedBook)
def return_book(book_id: int, user_id: int, db: Session = Depends(get_db)):
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    borrow_record = db.query(BorrowedBookModel).filter(
        BorrowedBookModel.book_id == book_id,
        BorrowedBookModel.user_id == user_id,
        BorrowedBookModel.return_date == None
    ).first()

    if not borrow_record:
        raise HTTPException(status_code=400, detail="No active borrow record found")

    book.quantity += 1
    book.available = True
    borrow_record.return_date = func.now()

    summary = db.query(BorrowSummaryModel).filter(BorrowSummaryModel.user_id == user_id).first()
    if summary and summary.borrow_count > 0:
        summary.borrow_count -= 1

    db.commit()
    db.refresh(borrow_record)
    return borrow_record

@app.get("/borrowed_books", response_model=List[BorrowedBook])
def list_borrowed_books(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(BorrowedBookModel)
    if user_id:
        query = query.filter(BorrowedBookModel.user_id == user_id)
    return query.all()

@app.get("/borrowed_books/summary_db", response_model=List[BorrowSummaryOut])
def get_summary_db(db: Session = Depends(get_db)):
    results = (
        db.query(
            BorrowSummaryModel.user_id,
            BorrowSummaryModel.borrow_count,
            UserModel.name,
            UserModel.email,
            UserModel.role
        )
        .join(UserModel, UserModel.id == BorrowSummaryModel.user_id)
        .all()
    )

    return [
        {
            "user_id": r.user_id,
            "name": r.name,
            "email": r.email,
            "role": r.role,
            "borrow_count": r.borrow_count
        }
        for r in results
    ]
