import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html directly
@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

# Initialize InfluxDB client
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://34.87.122.161:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "E-4XFMixUyHVbBp7C-xlbITeueQUINmWYm-Lfp4YHoV_nacIRq-bi3K0LiQ5ZAmlK4xRGdXYuuGjU8Xeseco3g==")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "emptywallet")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "jlog")

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN)

# Correct way to create a write API with default write options
write_api = client.write_api(write_options=WriteOptions(batch_size=10000, flush_interval=10_000))
query_api = client.query_api()

@app.post("/upload/")
async def upload_files(
    fileUpload1: UploadFile = File(...),
    fileUpload2: UploadFile = File(...),
    concurrent: int = Form(...),
    avg_response: int = Form(...),
    transition: int = Form(...),
    error_rate: int = Form(...),
):
    # อ่านเนื้อหาของไฟล์ที่อัปโหลด
    content1 = await fileUpload1.read()
    content2 = await fileUpload2.read()

    # นับจำนวนบรรทัดในแต่ละไฟล์
    num_lines1 = len(content1.splitlines())
    num_lines2 = len(content2.splitlines())

    # สร้างข้อมูลที่จะเขียนไปยัง InfluxDB
    point = Point("performance_test") \
        .tag("file1", fileUpload1.filename) \
        .tag("file2", fileUpload2.filename) \
        .field("num_lines_file1", num_lines1) \
        .field("num_lines_file2", num_lines2) \
        .field("concurrent_users", concurrent) \
        .field("avg_response_time", avg_response) \
        .field("transition", transition) \
        .field("error_rate", error_rate) \
        .time(write_precision=WritePrecision.MS)
    
    # เขียนข้อมูลไปยัง InfluxDB
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

    # ส่งข้อมูลกลับไปที่ frontend
    return JSONResponse(content={
        "file1": {
            "filename": fileUpload1.filename,
            "num_lines": num_lines1
        },
        "file2": {
            "filename": fileUpload2.filename,
            "num_lines": num_lines2
        },
        "concurrent": concurrent,
        "avg_response": avg_response,
        "transition": transition,
        "error_rate": error_rate
    })

@app.get("/metrics")
async def get_metrics():
    # Query to InfluxDB
    query = f'from(bucket: "{INFLUXDB_BUCKET}") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "performance_test")'
    tables = query_api.query(query)

    # ดึงค่าออกมาจากตาราง
    results = {}
    for table in tables:
        for record in table.records:
            if record.get_field() not in results:
                results[record.get_field()] = record.get_value()

    # ตัวอย่างการใช้ค่าที่ดึงมา
    avg_response = results.get('avg_response_time', 0)
    max_response = results.get('max_response_time', 0)  # ปรับให้ตรงกับฟิลด์ในฐานข้อมูล
    cpu_utilization = results.get('cpu_utilization', 0)  # ถ้ามีข้อมูลนี้ใน InfluxDB
    mem_utilization = results.get('mem_utilization', 0)  # ถ้ามีข้อมูลนี้ใน InfluxDB
    err_rate = results.get('error_rate', 0)

    # Check conditions for Conclusion and Problem/Solution
    conclusion = "PASS" if avg_response < 200 and err_rate < 5 else "FAIL"
    problem = "High Response Time" if avg_response > 200 else "None"
    solution = "Optimize backend processing" if problem != "None" else "No issues detected"

    # Output ที่จะส่งไปยัง frontend
    return JSONResponse(content={
        "avg_response": avg_response,
        "max_response": max_response,
        "cpu_utilization": cpu_utilization,
        "mem_utilization": mem_utilization,
        "err_rate": err_rate,
        "conclusion": conclusion,
        "problem": problem,
        "solution": solution
    })

# ใช้พอร์ตที่ได้จากตัวแปรแวดล้อม
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # ถ้าไม่มีตัวแปร PORT กำหนดค่าเริ่มต้นเป็น 8000
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
