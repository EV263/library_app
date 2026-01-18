import secrets

# 32-byte random key
secret_key = secrets.token_hex(32)
print(secret_key)

