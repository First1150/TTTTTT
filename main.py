from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Alternatively, if you want to serve the index.html directly
@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    # อ่านเนื้อหาของไฟล์ที่อัปโหลด
    content = await file.read()
    num_lines = len(content.splitlines())  # นับจำนวนบรรทัด
    
    # ส่งชื่อไฟล์และจำนวนบรรทัดกลับไปที่ frontend
    return JSONResponse(content={
        "filename": file.filename,
        "num_lines": num_lines
    })