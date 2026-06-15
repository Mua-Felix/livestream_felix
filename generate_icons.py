"""
Generate all PWA icons for LiveStream Felix
Run: python generate_icons.py
"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont
    import math

    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    output_dir = os.path.join(os.path.dirname(__file__), 'static', 'icons')
    os.makedirs(output_dir, exist_ok=True)

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background gradient (simulate with two rects)
        for i in range(size):
            ratio = i / size
            r = int(91 + (0 - 91) * ratio)
            g = int(110 + (212 - 110) * ratio)
            b = int(245 + (255 - 245) * ratio)
            draw.rectangle([0, i, size, i+1], fill=(r, g, b, 255))

        # Rounded corners mask
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        radius = size // 5
        mask_draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
        img.putalpha(mask)

        # Video camera icon (simple geometric)
        padding = size * 0.22
        cam_w = size - padding * 2
        cam_h = cam_w * 0.65
        cam_x = padding
        cam_y = (size - cam_h) / 2

        # Camera body
        body_r = cam_w * 0.08
        draw.rounded_rectangle(
            [cam_x, cam_y, cam_x + cam_w * 0.68, cam_y + cam_h],
            radius=int(body_r),
            fill=(255, 255, 255, 230)
        )

        # Camera lens
        lens_cx = cam_x + cam_w * 0.34
        lens_cy = cam_y + cam_h * 0.5
        lens_r = cam_h * 0.28
        draw.ellipse(
            [lens_cx - lens_r, lens_cy - lens_r, lens_cx + lens_r, lens_cy + lens_r],
            fill=(91, 110, 245, 200)
        )
        inner_r = lens_r * 0.5
        draw.ellipse(
            [lens_cx - inner_r, lens_cy - inner_r, lens_cx + inner_r, lens_cy + inner_r],
            fill=(255, 255, 255, 180)
        )

        # Camera viewfinder triangle
        vf_x = cam_x + cam_w * 0.72
        vf_y = cam_y + cam_h * 0.2
        vf_w = cam_w * 0.28
        vf_h = cam_h * 0.6
        draw.polygon([
            (vf_x, vf_y),
            (vf_x + vf_w, vf_y + vf_h * 0.3),
            (vf_x + vf_w, vf_y + vf_h * 0.7),
            (vf_x, vf_y + vf_h),
        ], fill=(255, 255, 255, 200))

        # Save
        icon_path = os.path.join(output_dir, f'icon-{size}.png')
        img.save(icon_path, 'PNG')
        print(f'✅ Generated icon-{size}.png')

    print(f'\n🎉 All {len(sizes)} icons generated in {output_dir}')

except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
    print("Then run: python generate_icons.py")
except Exception as e:
    print(f"Error: {e}")
    # Fallback: create simple colored square icons
    try:
        from PIL import Image, ImageDraw
        sizes = [72, 96, 128, 144, 152, 192, 384, 512]
        output_dir = os.path.join(os.path.dirname(__file__), 'static', 'icons')
        os.makedirs(output_dir, exist_ok=True)
        for size in sizes:
            img = Image.new('RGB', (size, size), (91, 110, 245))
            draw = ImageDraw.Draw(img)
            # Simple F text
            draw.rectangle([size//3, size//4, size*2//3, size*3//4], fill=(255,255,255))
            img.save(os.path.join(output_dir, f'icon-{size}.png'))
            print(f'✅ Simple icon-{size}.png')
    except Exception as e2:
        print(f'Fallback also failed: {e2}')
