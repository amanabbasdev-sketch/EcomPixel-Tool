import os
import shutil
import uuid
import zipfile
import asyncio
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.core import process_single_image

app = FastAPI(title="EcomPixel Tool")

TEMP_DIR = "static/temp"
os.makedirs(TEMP_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('static/dashboard.html')

# ✅ SEO: Robots.txt (Google ko batane ke liye ki kya crawl karna hai)
@app.get("/robots.txt")
def robots_txt():
    content = """User-agent: *
Allow: /
Sitemap: https://ecompixel-tool.onrender.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")

# ✅ SEO: Sitemap.xml (Site ka map)
@app.get("/sitemap.xml")
def sitemap_xml():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://ecompixel-tool.onrender.com/</loc>
    <lastmod>2026-01-29</lastmod>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content=content, media_type="application/xml")

async def remove_file_after_delay(path: str, delay: int = 600):
    await asyncio.sleep(delay)
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception:
        pass

@app.post("/process")
async def process_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    watermark: UploadFile = File(None),
    output_format: str = Form("PNG"),
    should_remove_bg: bool = Form(True),
    resize_mode: str = Form("original"),
    custom_w: int = Form(0),
    custom_h: int = Form(0),
    target_file_size: float = Form(0), 
    size_unit: str = Form("KB")        
):
    session_id = str(uuid.uuid4())
    user_folder = os.path.join(TEMP_DIR, session_id)
    os.makedirs(user_folder, exist_ok=True)

    watermark_data = await watermark.read() if watermark else None
    processed_files_info = []
    
    target_kb = 0
    if target_file_size > 0:
        if size_unit == "MB":
            target_kb = int(target_file_size * 1024)
        else:
            target_kb = int(target_file_size)

    ext = ".png"
    if output_format == "JPEG": ext = ".jpg"
    if output_format == "WEBP": ext = ".webp"
    if output_format == "BMP": ext = ".bmp"

    zip_filename = "EcomPixel_Results.zip"
    zip_path = os.path.join(user_folder, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            content = await file.read()
            processed_bytes = process_single_image(
                content, 
                watermark_data, 
                output_format, 
                should_remove_bg,
                resize_mode,
                custom_w,
                custom_h,
                target_kb 
            )
            
            if processed_bytes:
                original_name = os.path.splitext(file.filename)[0]
                safe_name = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_')).strip()
                if len(safe_name) > 50: safe_name = safe_name[:50]
                
                filename = safe_name + ext
                file_path = os.path.join(user_folder, filename)
                
                with open(file_path, "wb") as f:
                    f.write(processed_bytes)
                zip_file.write(file_path, arcname=filename)
                
                actual_size_kb = os.path.getsize(file_path) / 1024
                
                processed_files_info.append({
                    "name": filename,
                    "url": f"/static/temp/{session_id}/{filename}",
                    "size": f"{actual_size_kb:.1f} KB" 
                })

    background_tasks.add_task(remove_file_after_delay, user_folder)

    return JSONResponse(content={
        "status": "success",
        "zip_url": f"/static/temp/{session_id}/{zip_filename}",
        "images": processed_files_info
    })