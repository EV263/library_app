class User:
    def __init__(self, name, email, role="student"):
        self.name = name
        self.email = email
        self.role = role

    def get_role(self):
        return self.role


class Student(User):
    def borrow_book(self, book):
        return f"{self.name} borrowed the book: {book}"


class Admin(User):
    def add_book(self, book):
        return f"{self.name} added the book: {book}"

    def remove_book(self, book):
        return f"{self.name} removed the book: {book}"

