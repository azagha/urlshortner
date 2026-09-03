import string
import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import pymysql

from models import UserCreate, UrlCreate, UrlResponse
from database import get_db_connection

app = FastAPI()

def generate_short_code(length: int = 5) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db = Depends(get_db_connection)):
    try:
        with db.cursor() as cursor:
            sql = """
                INSERT INTO USERS (first_name, last_name, email)
                VALUES(%s, %s, %s)
            """
            cursor.execute(sql, (user.first_name, user.last_name, user.email))
            db.commit()
            return {"message": "User Registered Succesfully"}
    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")


@app.post("/shorten", status_code=status.HTTP_201_CREATED)
def shorten_url(payload: UrlCreate, db = Depends(get_db_connection)):
    try:
        with db.cursor() as cursor:
            if payload.user_id is not None:
                check_sql = """
                    SELECT shortened_url
                    FROM urls
                    WHERE original_url = %s AND user_id = %s
                    LIMIT 1
                """
                cursor.execute(
                check_sql, (payload.original_url, payload.user_id)
                )
                existing_record = cursor.fetchone()

                if existing_record:
                    return {
                        "original_url": payload.original_url,
                        "shortened_url": existing_record["shortened_url"],
                    }

            #new URL
            while True:
                short_code = generate_short_code(5)
                cursor.execute(
                    "SELECT 1 FROM urls WHERE shortened_url = %s LIMIT 1",
                    (short_code,),
                )
                if not cursor.fetchone():
                    break


            insert_sql = """
                INSERT INTO urls (original_url, shortened_url, click_count, created_at, user_id)
                VALUES (%s, %s, 0, NOW(),%s)
            """
            cursor.execute(
                insert_sql, (payload.original_url, short_code, payload.user_id)
            )
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
            select_sql = """
                SELECT original_url
                FROM urls
                WHERE shortened_url = %s
                LIMIT 1
            """

            cursor.execute(select_sql, (short_code,))
            record = cursor.fetchone()

            if not record:
                raise HTTPException(status_code=404, detail="URL not found")

            update_sql = """
                UPDATE urls
                SET click_count = click_count + 1, last_opened = NOW()
                WHERE shortened_url = %s
            """

            cursor.execute(update_sql, (short_code,))
            db.commit()

            #adding https to the link
            target_url = record["original_url"]
            if not target_url.startswith(("http://", "https://")):
                target_url = f"https://{target_url}"

            return RedirectResponse(
                url = target_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
            )
    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}" )