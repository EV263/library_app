-- Create database
CREATE DATABASE IF NOT EXISTS library_db;
USE library_db;

-- =====================
-- Table: books
-- =====================
CREATE TABLE books (
    id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    category VARCHAR(255),
    available TINYINT(1) DEFAULT 1,
    quantity INT DEFAULT 1,
    PRIMARY KEY (id)
);

-- =====================
-- Table: users
-- =====================
CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    role ENUM('student','admin') NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
);

-- =====================
-- Table: borrow_summary
-- =====================
CREATE TABLE borrow_summary (
    user_id INT NOT NULL AUTO_INCREMENT,
    borrow_count INT,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_borrow_summary_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- =====================
-- Table: borrowed_books
-- =====================
CREATE TABLE borrowed_books (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    return_date TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_user_id (user_id),
    KEY idx_book_id (book_id),
    CONSTRAINT fk_borrowed_books_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_borrowed_books_book
        FOREIGN KEY (book_id)
        REFERENCES books(id)
        ON DELETE CASCADE
);

