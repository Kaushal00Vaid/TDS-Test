from fastapi import FastAPI, Request
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
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
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

def percentile(values, p):
    if not values:
        return 0
    values = sorted(values)
    k = math.ceil((p / 100) * len(values)) - 1
    return values[max(0, k)]


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
    
    return results

