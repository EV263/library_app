from fastapi import FastAPI, Depends, HTTPException
from auth import create_access_token, verify_token
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection

app = FastAPI()

# Allow frontend (Next.js) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],  # frontend ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register")
def register(name: str, email: str, role: str = "student"):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (name, email, role) VALUES (%s, %s, %s)",
            (name, email, role)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    return {"message": f"User {name} registered successfully with role {role}"}

@app.post("/login")
def login(email: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, email, role FROM users WHERE email=%s", (email,))
    user_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token with role + user_id
    token = create_access_token({
        "sub": user_data["email"],
        "role": user_data["role"],
        "user_id": user_data["id"]
    })

    return {"access_token": token, "token_type": "bearer"}

@app.get("/protected")
def protected_route(token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch user info from DB
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, role FROM users WHERE email=%s", (payload["sub"],))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message": f"Hello {user_data['email']}, role: {user_data['role']}",
        "role": user_data["role"],
        "user_id": user_data["id"],
        "email": user_data["email"]
    }
