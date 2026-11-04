from app.models.user import Role, User


class UserRepository:
    """Saves and loads Users as (:User) nodes. The rest of the app never sees Neo4j."""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, id):
        row = self.db.query_one("MATCH (u:User {id: $id}) RETURN u", id=id)
        return self._to_user(row)

    def get_by_email(self, email):
        row = self.db.query_one("MATCH (u:User {email: $email}) RETURN u", email=email)
        return self._to_user(row)

    def add(self, user):
        # A second user with the same id or e-mail gives IntegrityError (constraints in db.py).
        self.db.query(
            """
            CREATE (:User {id: $id, name: $name, email: $email, passwordHash: $password_hash, role: $role})
            """,
            id=user.id,
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role.value,
        )

    def _to_user(self, row):
        if row is None:
            return None
        u = row["u"]
        return User(
            id=u["id"],
            name=u["name"],
            email=u["email"],
            password_hash=u["passwordHash"],
            role=Role(u["role"]),
        )
