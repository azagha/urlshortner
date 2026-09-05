import string
import services
import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

import pymysql

from models import UserCreate, UrlCreate, UrlResponse
from database import get_db_connection

app = FastAPI()

password_hash = PasswordHash((BcryptHasher(),))
security = HTTPBasic(auto_error=False)

def authenticate_user(
    credentials: HTTPBasicCredentials | None = Depends(security),
    db=Depends(get_db_connection)
) -> dict | None:
    if credentials is None:
        return None

    with db.cursor() as cursor:
        user = services.get_user_by_email(cursor, credentials.username)

        if not user or not services.verify_user_password(credentials.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate" :"Basic"}
            )
        return user


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db = Depends(get_db_connection)):
    try:
        with db.cursor() as cursor:
            services.create_user(
                cursor, user.first_name, user.last_name, user.email, user.password
            )
            db.commit()
            return {"message": "User Registered Succesfully"}
    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")





@app.post("/shorten", status_code=status.HTTP_201_CREATED)
def shorten_url(payload: UrlCreate, 
                current_user: dict | None = Depends(authenticate_user),
                db = Depends(get_db_connection)
):
    try:
        with db.cursor() as cursor:
            user_id = current_user["user_id"] if current_user else None
            if user_id is not None:
                existing_record = services.get_existing_url(cursor, payload.original_url, user_id)
                if existing_record:
                    return {
                        "original_url": payload.original_url,
                        "shortened_url": existing_record["shortened_url"],
                    }

            

            short_code = services.insert_short_url(cursor, payload.original_url, user_id)
            db.commit()

            return {
                "original_url": payload.original_url,
                "shortened_url": short_code,
            }

    except pymysql.MySQLError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")


@app.get("/{short_code}")
def redirect_to_url(short_code: str, db=Depends(get_db_connection)):
    try:
        with db.cursor() as cursor:
            original_url = services.get_url_and_track_click(cursor, short_code)

            if not original_url:
                raise HTTPException(status_code=404, detail="URL not found")

            db.commit()

            if not original_url.startswith(("http://", "https://")):
                original_url = f"https://{original_url}"

            return RedirectResponse(
                url = original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
            )
    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}" )


@app.delete("/urls/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url(
    short_code: str,
    current_user: dict | None = Depends(authenticate_user),
    db = Depends(get_db_connection),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to delete url",
            headers={"WWW-Authenticate": "Basic"}
        )
    
    try:
        with db.cursor() as cursor:
            result = services.delete_url(
                cursor, short_code, current_user["user_id"]
            )

            if result == "NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="URL not found"
                )

            if result == "FORBIDDEN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to delete this URL",
                )

            db.commit()
            return None
    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/admin/dashboard")
def admin_dashboard(
    current_user: dict | None = Depends(authenticate_user),
    db = Depends(get_db_connection),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access requied",
        )

    try:
        with db.cursor() as cursor:
            return services.get_admin_dashboard(cursor)
    except pymysql.MySQLError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")