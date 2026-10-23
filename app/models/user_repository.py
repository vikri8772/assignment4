from app.models.user import Role, User


class UserRepository:
    """Saves and loads Users. The rest of the app never sees the users table."""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, id):
        row = self.db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
        return self._to_user(row)

    def get_by_email(self, email):
        row = self.db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return self._to_user(row)

    def add(self, user):
        with self.db:
            self.db.execute(
                "INSERT INTO users (id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (user.id, user.name, user.email, user.password_hash, user.role.value),
            )

    def _to_user(self, row):
        if row is None:
            return None
        return User(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=Role(row["role"]),
        )
