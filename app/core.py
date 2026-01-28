from rembg import remove, new_session
from PIL import Image
import io

# Lite Model: Crash hone se bachayega
session = new_session("u2netp") 

def process_single_image(image_bytes, watermark_data, output_format, should_remove_bg, resize_mode, custom_w, custom_h, target_kb):
    try:
        # 1. Background Removal
        if should_remove_bg:
            output_data = remove(image_bytes, session=session)
            img = Image.open(io.BytesIO(output_data)).convert("RGBA")
        else:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

        # 2. Smart Resizing (New Logic)
        if resize_mode == "standard":
            img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
        elif resize_mode == "insta_sq":
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        elif resize_mode == "insta_story":
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        elif resize_mode == "custom" and custom_w > 0 and custom_h > 0:
            img = img.resize((custom_w, custom_h), Image.Resampling.LANCZOS)

        # 3. Format Handling (Transparency Logic)
        final_img = img
        save_format = "PNG" # Default
        save_params = {}

        if output_format == "JPEG" or output_format == "BMP":
            # Inme Transparency nahi hoti -> White Background add karo
            background = Image.new("RGB", final_img.size, (255, 255, 255))
            if final_img.mode == 'RGBA':
                background.paste(final_img, mask=final_img.split()[3])
            else:
                background.paste(final_img)
            final_img = background
            save_format = output_format
        
        elif output_format == "WEBP":
            save_format = "WEBP" # Supports transparency
        
        else:
            save_format = "PNG"

        # 4. Compression
        output_io = io.BytesIO()
        if target_kb > 0 and output_format in ["JPEG", "WEBP"]:
            quality = 95
            while quality > 10:
                output_io.seek(0)
                output_io.truncate()
                final_img.save(output_io, format=save_format, quality=quality, **save_params)
                if (output_io.tell() / 1024) <= target_kb:
                    break
                quality -= 5
        else:
            # Max Quality
            final_img.save(output_io, format=save_format, quality=100)

        return output_io.getvalue()

    except Exception as e:
        print(f"Error: {e}")
        return None