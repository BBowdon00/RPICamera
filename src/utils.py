import logging
from PIL import Image, ImageDraw, ImageFont
import time

def setup_logging(level):
    logging.basicConfig(level=getattr(logging, level.upper(), "INFO"),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def overlay_timestamp(img, font):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    draw = ImageDraw.Draw(img, "RGBA")
    text_bbox = draw.textbbox((0, 0), timestamp, font=font)
    background_box = (10, 10, 10 + (text_bbox[2] - text_bbox[0]) + 20, 10 + (text_bbox[3] - text_bbox[1]) + 20)
    draw.rectangle(background_box, fill=(0, 0, 0, 128))  # Semi-transparent black box
    draw.text((20, 20), timestamp, font=font, fill="red")
    return img

