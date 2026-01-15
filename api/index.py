from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import csv
import json
import math
import os

app = FastAPI()


# Enable CORS for all origins (GET only is enforced by route method)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Access-Control-Allow-Origin"]
)

BASE_DIR = os.path.dirname(__file__)
LATENCY_FILE = os.path.join(BASE_DIR, "..", "q-vercel-latency.json")
CSV_FILE = os.path.join(BASE_DIR, "..", "q-fastapi.csv")

def load_students():
    students = []
    with open(CSV_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append({
                "studentId": int(row["studentId"]),
                "class": row["class"]
            })
    return students

# Explicit OPTIONS handler (critical on Vercel)
@app.options("/{path:path}")
async def options_handler(path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )

def percentile(values, p):
    if not values:
        return 0

    values = sorted(values)
    n = len(values)

    # position using linear interpolation (NumPy/Pandas default)
    pos = (p / 100) * (n - 1)
    lower = math.floor(pos)
    upper = math.ceil(pos)

    if lower == upper:
        return values[int(pos)]

    weight = pos - lower
    return values[lower] * (1 - weight) + values[upper] * weight


@app.get("/api")
async def get_students(req: Request):
    students = load_students()
    print(students)
    classes = req.query_params.getlist("class")

    if classes:
        students = [s for s in students if s["class"] in classes]

    return {"students": students}

@app.post("/api/latency")
async def post_latency(req: Request):
    body = await req.json()
    regions = body["regions"]
    threshold = body['threshold_ms']

    with open(LATENCY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = {}

    for r in regions:
        records = [x for x in data if x["region"] == r]

        latencies = [x["latency_ms"] for x in records]
        uptimes = [x["uptime_pct"] for x in records]

        results[r] = {
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "p95_latency": percentile(latencies, 95),
            "avg_uptime": sum(uptimes) / len(uptimes) if uptimes else 0,
            "breaches": sum(1 for x in latencies if x > threshold),
        }
    
    return {"regions": results}

