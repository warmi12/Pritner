import numpy as np

def floyd_steinberg(image):
    # image: np.array of shape (height, width), dtype=float, 0.0-1.0
    h, w = image.shape
    for y in range(h):
        for x in range(w):
            old = image[y, x]
            new = np.round(old)
            image[y, x] = new
            error = old - new
            # precomputing the constants helps
            if x + 1 < w:
                image[y, x + 1] += error * 0.4375 # right, 7 / 16
            if (y + 1 < h) and (x + 1 < w):
                image[y + 1, x + 1] += error * 0.0625 # right, down, 1 / 16
            if y + 1 < h:
                image[y + 1, x] += error * 0.3125 # down, 5 / 16
            if (x - 1 >= 0) and (y + 1 < h):
                image[y + 1, x - 1] += error * 0.1875 # left, down, 3 / 16
    return image


from PIL import Image, ImageOps, ImageDraw

def pil_to_np(pilimage):
    return np.array(pilimage) / 255

def np_to_pil(image):
    return Image.fromarray((image * 255).astype('uint8'))

def scaleImg(scalePercent,img):
    width = int(img.size[0] * scalePercent / 100)
    height = int(img.size[1] * scalePercent / 100)
    # width = 640 maximum values for printer
    # height = 853
    dim = (width, height)
    resized = img.resize(dim)

    return resized

def replaceValues(img):
    for i in range(0, img.shape[0]):  # changing 1 into 0 and 0 into 1
            img[i] = 1 - img[i]
        
    return img

def floyd_steinberg_combined(scalePercent,imgName):
    imgStatue = Image.open("F:\\Printer\\finalPrinterProject\\pictures\\"+imgName+".png").convert('L')
    imgStatue = scaleImg(scalePercent,imgStatue)

    imgStatue = pil_to_np(imgStatue)
    imgStatue = floyd_steinberg(imgStatue)
    imgStatue = np_to_pil(imgStatue)

###CIRCULAR IMG START###
    if imgName != "thank":
        scaledShape = (imgStatue.size[0], imgStatue.size[1])

        #preparation of a round mask
        mask = Image.new('L', scaledShape, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + scaledShape, fill=1) #ones inside

        mask = np.array(mask.getdata())
        mask = replaceValues(mask) #ones outside = white (not for printer)

        img = np.array(imgStatue.getdata())
        img = np.logical_or(img, mask) #applying the mask

        imgStatue=np.reshape(img,scaledShape)
        imgStatue = np_to_pil(imgStatue)
###STOP###

    imgStatue.save("F:\\Printer\\finalPrinterProject\\pictures\\"+imgName+"_dithering.png")






