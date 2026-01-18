from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, create_engine, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI()

# -----------------------------
# CORS setup
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for frontend origin if needed
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

class BorrowedBookModel(Base):
    __tablename__ = "borrowed_books"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    borrow_date = Column(TIMESTAMP, server_default=func.now())
    return_date = Column(TIMESTAMP, nullable=True)

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
    class Config:
        orm_mode = True

class BorrowedBook(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrow_date: str
    return_date: Optional[str]
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

# List all books
@app.get("/books", response_model=List[Book])
def list_books(db: Session = Depends(get_db)):
    books = db.query(BookModel).all()
    # Ensure available is always boolean
    for b in books:
        b.available = bool(b.available)
    return books

# Add a new book
@app.post("/books", response_model=Book)
def add_book(book: Book, db: Session = Depends(get_db)):
    db_book = BookModel(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

# Borrow a book
@app.post("/books/{book_id}/borrow", response_model=BorrowedBook)
def borrow_book(book_id: int, user_id: int, db: Session = Depends(get_db)):
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.available:
        raise HTTPException(status_code=400, detail="Book already borrowed")

    book.available = False
    db.commit()

    borrow_record = BorrowedBookModel(user_id=user_id, book_id=book_id)
    db.add(borrow_record)
    db.commit()
    db.refresh(borrow_record)
    return borrow_record

# Return a book
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

    book.available = True
    borrow_record.return_date = func.now()
    db.commit()
    db.refresh(borrow_record)
    return borrow_record

# Borrow history (admin or student)
@app.get("/borrowed_books", response_model=List[BorrowedBook])
def list_borrowed_books(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(BorrowedBookModel)
    if user_id:
        query = query.filter(BorrowedBookModel.user_id == user_id)
    return query.all()
