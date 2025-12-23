from services.auth import create_user

create_user(
    username="admin",
    email="admin@chumcred.com",
    password="admin123",
    role="admin"
)

print("Admin created: admin / admin123")
