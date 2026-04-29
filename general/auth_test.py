import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

print("admin:", hash_password("admin123"))
print("client1:", hash_password("client123"))
print("viewer:", hash_password("viewer123"))