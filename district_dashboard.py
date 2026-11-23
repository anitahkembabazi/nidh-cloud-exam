from functools import lru_cache
from html import escape
from secrets import compare_digest
from time import monotonic

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from psycopg.rows import dict_row

router = APIRouter()
security = HTTPBasic(auto_error=False)
DATABASE_URL = "postgresql://root@127.0.0.1:26257/nidh?sslmode=disable"

# Mock accounts for the local synthetic-data demonstration.
DEMO_USERS = {
    "district01": ("clinic-demo", "district_officer", "D001"),
    "national": ("analyst-demo", "national_analyst", None),
}


def audit(username, role, endpoint, scope, outcome):
    with psycopg.connect(DATABASE_URL) as db:
        db.execute(
            """
            INSERT INTO read_audit
                (username, role_name, endpoint, district_scope, outcome)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username, role, endpoint, scope, outcome),
        )


def read_scope(
    request: Request,
    district: str | None = None,
    credentials: HTTPBasicCredentials | None = Depends(security),
):
    username = credentials.username if credentials else ""
    account = DEMO_USERS.get(username)

    if account is None or not compare_digest(
        credentials.password.encode("utf-8"), account[0].encode("utf-8")
    ):
        audit(username or "anonymous", "unknown", request.url.path,
              district or "all", "denied")
        raise HTTPException(
            status_code=401,
            detail="Sign in with a demo account.",
            headers={"WWW-Authenticate": "Basic"},
        )

    _, role, assigned_district = account
    if assigned_district and district and district != assigned_district:
        audit(username, role, request.url.path, district, "denied")
        raise HTTPException(status_code=403, detail="District access denied.")

    scope = assigned_district or district
    audit(username, role, request.url.path, scope or "all", "allowed")
    return scope


@lru_cache(maxsize=32)
def load_totals(scope, refresh_period):
    query = """
        SELECT district_id, vaccine_code, count(*) AS doses
        FROM vaccination_dose
        WHERE district_id IS NOT NULL
    """
    parameters = ()
    if scope is not None:
        query += " AND district_id = %s"
        parameters = (scope,)

    query += " GROUP BY district_id, vaccine_code ORDER BY district_id, vaccine_code"

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as db:
        return db.execute(query, parameters).fetchall()


@router.get("/api/district-totals")
def district_totals(scope: str | None = Depends(read_scope)):
    return load_totals(scope, int(monotonic() // 30))


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(scope: str | None = Depends(read_scope)):
    totals = load_totals(scope, int(monotonic() // 30))
    rows = "".join(
        f"<tr><td>{escape(row['district_id'])}</td>"
        f"<td>{escape(row['vaccine_code'])}</td><td>{row['doses']}</td></tr>"
        for row in totals
    )
    return f"""<!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="30">
        <title>NIDH district vaccinations</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 48rem;
                    margin: 3rem auto; padding: 0 1rem; color: #17352d; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ text-align: left; padding: .8rem; border-bottom: 1px solid #ccd8d3; }}
            th {{ background: #eaf3ef; }}
        </style>
    </head>
    <body>
        <h1>District vaccination totals</h1>
        <p>District scope: {escape(scope or "All districts")}</p>
        <table>
            <thead><tr><th>District</th><th>Vaccine</th><th>Recorded doses</th></tr></thead>
            <tbody>{rows or '<tr><td colspan="3">No district records yet.</td></tr>'}</tbody>
        </table>
    </body>
    </html>"""