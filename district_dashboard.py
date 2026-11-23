from functools import lru_cache
from html import escape
from time import monotonic

import psycopg
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from psycopg.rows import dict_row

router = APIRouter()
DATABASE_URL = "postgresql://root@127.0.0.1:26257/nidh?sslmode=disable"


@lru_cache(maxsize=1)
def load_totals(refresh_period):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as db:
        return db.execute("""
            SELECT district_id, vaccine_code, count(*) AS doses
            FROM vaccination_dose
            WHERE district_id IS NOT NULL
            GROUP BY district_id, vaccine_code
            ORDER BY district_id, vaccine_code
        """).fetchall()


@router.get("/api/district-totals")
def district_totals():
    # Requests in the same 30-second period share one database result.
    return load_totals(int(monotonic() // 30))


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    rows = "".join(
        f"<tr><td>{escape(row['district_id'])}</td>"
        f"<td>{escape(row['vaccine_code'])}</td>"
        f"<td>{row['doses']}</td></tr>"
        for row in district_totals()
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
        <table>
            <thead><tr><th>District</th><th>Vaccine</th><th>Recorded doses</th></tr></thead>
            <tbody>{rows or '<tr><td colspan="3">No district records yet.</td></tr>'}</tbody>
        </table>
    </body>
    </html>"""