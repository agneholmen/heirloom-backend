from PIL import Image
import os

img_dir = '../heirloom-frontend/public/images/'
for f in ['male.png', 'female.png', 'unknown.png']:
    img = Image.open(os.path.join(img_dir, f))
    print(f'{f}: {img.size}')
