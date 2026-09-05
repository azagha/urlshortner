import string
import secrets
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

password_hash = PasswordHash((BcryptHasher(),))


def generate_short_code(length: int = 5) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def create_user(cursor, first_name: str, last_name: str, email: str, password: str):
    hashed_password = password_hash.hash(password)
    sql = """
        INSERT INTO users (first_name, last_name, email, password)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (first_name, last_name, email, hashed_password))


def get_user_by_email(cursor, email: str):
    sql = "SELECT user_id, email, password FROM users WHERE email = %s LIMIT 1"
    cursor.execute(sql, (email,))
    return cursor.fetchone()


def verify_user_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_existing_url(cursor, original_url: str, user_id: int):
    sql = """
        SELECT shortened_url
        FROM urls
        WHERE original_url = %s AND user_id = %s
        LIMIT 1
    """
    cursor.execute(sql, (original_url, user_id))
    return cursor.fetchone()


def insert_short_url(cursor, original_url: str, user_id: int | None) -> str:
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
        VALUES (%s, %s, 0, NOW(), %s)
    """
    cursor.execute(insert_sql, (original_url, short_code, user_id))
    return short_code


def get_url_and_track_click(cursor, short_code: str):
    select_sql = """
        SELECT original_url
        FROM urls
        WHERE shortened_url = %s
        LIMIT 1
    """
    cursor.execute(select_sql, (short_code,))
    record = cursor.fetchone()

    if not record:
        return None

    update_sql = """
        UPDATE urls
        SET click_count = click_count + 1, last_opened = NOW()
        WHERE shortened_url = %s
    """
    cursor.execute(update_sql, (short_code,))
    return record["original_url"]


def delete_url(cursor, short_code: str, user_id: int) -> str:
    select_sql = """
        SELECT user_id
        FROM urls
        WHERE shortened_url = %s
        LIMIT 1
    """
    cursor.execute(select_sql, (short_code,))
    record = cursor.fetchone()

    if not record:
        return "NOT_FOUND"

    if record["user_id"] != user_id:
        return "FORBIDDEN"
    
    delete_sql = """
        DELETE FROM urls
        WHERE shortened_url = %s AND user_id = %s
    """

    cursor.execute(delete_sql, (short_code, user_id))
    return "DELETED"