# 📚 Library Management System

A command-line **Library Management System** built with **Python** and **SQLite**, supporting two roles — **Admin** and **Member** — with full book, author, member, and transaction management.

## Features

### 🔐 Authentication
- User registration with role selection (`admin` / `member`)
- Secure password entry using `getpass` (hidden input)
- Login with username/password validation

### 🛠️ Admin Menu
- Add, view, update, and delete **authors**
- Add, view, update, and delete **books**
- View and delete **members**
- View all **transactions**
- View **overdue books** across all members

### 👤 Member Menu
- View all available books
- Search books by title
- Borrow a book (with issue date and due date)
- Return a borrowed book
- View personal overdue books

## Database Schema

The app uses a local SQLite database (`library.db`) with the following tables:

| Table          | Description                                      |
|----------------|---------------------------------------------------|
| `user`         | Stores usernames, passwords, and roles            |
| `author`       | Stores author names                                |
| `books`        | Stores book details, linked to an author           |
| `transactions` | Tracks book issue/return records and status        |

Tables are created automatically on first run if they don't already exist.

## Requirements

- Python 3.x
- No external dependencies — uses only the standard library:
  - `sqlite3`
  - `getpass`
  - `datetime`

## Getting Started

1. Clone the repository
   ```bash
   git clone <your-repo-url>
   cd <your-repo-folder>
   ```

2. Run the application
   ```bash
   python library_management.py
   ```

3. Follow the on-screen menu:
   - Register a new user (choose `admin` or `member` role)
   - Log in with your credentials
   - Navigate the Admin or Member menu based on your role

## Usage Notes

- Dates (issue date, due date, return date) must be entered in `YYYY-MM-DD` format.
- A book can only be borrowed if its `available` count is greater than zero.
- Overdue books are determined by comparing the `due_date` to the current system date.
- The database file (`library.db`) is created automatically in the project directory on first run.

## Project Structure

```
.
├── library_management.py   # Main application script
├── library.db               # SQLite database (auto-generated)
└── README.md
```

## Future Improvements

- Password hashing instead of plain-text storage
- Input validation for dates and IDs
- Fine calculation for overdue books
- GUI or web-based interface

## License

This project is open-source and available under the [MIT License](LICENSE).
