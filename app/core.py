from PIL import Image
import io
import gc  # Garbage Collector interface

# Lite Model: Initialize only when needed
session = None

def _initialize_session():
    """Lazy initialization of rembg session"""
    global session
    if session is None:
        try:
            from rembg import new_session
            # 'u2netp' is the smallest model available
            session = new_session("u2netp")
        except Exception as e:
            print(f"Warning: Could not initialize rembg session: {e}")
            raise

def _get_remove():
    """Get the remove function from rembg"""
    try:
        from rembg import remove
        return remove
    except Exception as e:
        print(f"Error: Could not import rembg remove function: {e}")
        raise 

def process_single_image(image_bytes, watermark_data, output_format, should_remove_bg, resize_mode, custom_w, custom_h, target_kb):
    try:
        # Optimization: Open image with reduced limit to prevent decompression bomb errors
        Image.MAX_IMAGE_PIXELS = None 
        
        input_image = Image.open(io.BytesIO(image_bytes))
        
        # Immediate resize if image is massive (save RAM before processing)
        if input_image.width > 2500 or input_image.height > 2500:
            input_image.thumbnail((2500, 2500), Image.Resampling.LANCZOS)

        img = input_image.convert("RGBA")
        
        # 1. Background Removal
        if should_remove_bg:
            _initialize_session()
            remove = _get_remove()
            # Pass the PIL image directly to save conversion steps
            img = remove(img, session=session)

        # 2. Smart Resizing
        if resize_mode == "standard":
            img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
        elif resize_mode == "insta_sq":
            img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        elif resize_mode == "insta_story":
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        elif resize_mode == "custom" and custom_w > 0 and custom_h > 0:
            img = img.resize((custom_w, custom_h), Image.Resampling.LANCZOS)

        # 3. Format Handling
        final_img = img
        save_format = "PNG"
        save_params = {}

        if output_format == "JPEG" or output_format == "BMP":
            background = Image.new("RGB", final_img.size, (255, 255, 255))
            if final_img.mode == 'RGBA':
                background.paste(final_img, mask=final_img.split()[3])
            else:
                background.paste(final_img)
            final_img = background
            save_format = output_format
        elif output_format == "WEBP":
            save_format = "WEBP"
        else:
            save_format = "PNG"

        # 4. Compression
        output_io = io.BytesIO()
        if target_kb > 0 and output_format in ["JPEG", "WEBP"]:
            quality = 85  # Start lower to save memory
            while quality > 10:
                output_io.seek(0)
                output_io.truncate()
                final_img.save(output_io, format=save_format, quality=quality, **save_params)
                if (output_io.tell() / 1024) <= target_kb:
                    break
                quality -= 10
        else:
            final_img.save(output_io, format=save_format, quality=90) # Default optimized quality

        # Cleanup Memory
        del input_image
        del img
        if 'background' in locals(): del background
        del final_img
        gc.collect()

        return output_io.getvalue()

    except Exception as e:
        print(f"Error processing image: {e}")
        return None