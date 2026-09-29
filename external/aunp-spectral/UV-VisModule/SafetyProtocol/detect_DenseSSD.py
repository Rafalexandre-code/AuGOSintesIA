import warnings

import torch

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from PIL import Image, ImageDraw, ImageFont
from model.denseSSD import denseSSD
from torchvision import transforms
from utils.image_process import *
import config_denseSSD as config
import os
import cv2
import numpy as np
import time


# Load model checkpoint
model_path = config.model_path
model = denseSSD(n_classes=config.C)
model.load_state_dict(torch.load(model_path))
model.to(config.device)
model.eval()

# Transforms
resize = transforms.Resize((config.image_size, config.image_size))
to_tensor = transforms.ToTensor()
normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])


def visualize_detection(original_image, min_score, max_overlap, top_k, path=None):
    """
    :return False or image(True) (boolean)
    """

    image = normalize(to_tensor(resize(original_image))).to(config.device)

    start = time.time()
    with torch.no_grad():
        predicted_locs, predicted_scores = model(image.unsqueeze(0).to(config.device))
    end = time.time()

    bboxes, labels, _ = detect_objects(model, predicted_locs.to(config.device), predicted_scores.to(config.device), min_score=min_score,
                                       max_overlap=max_overlap, top_k=top_k)

    if labels == ['background']: # tip is not detect
        return False

    else:
        bboxes = bboxes[0].to('cpu')

        original_dims = torch.FloatTensor(
            [original_image.width, original_image.height, original_image.width, original_image.height]).unsqueeze(0)
        bboxes = bboxes * original_dims

        # Decode class integer labels
        labels = [label_class[i] for i in labels[0].to('cpu').tolist()]

        draw_label = ImageDraw.Draw(original_image)
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 15, encoding="unic")

        for i in range(bboxes.size(0)):
            bboxes_coor = bboxes[i].tolist()
            draw_label.rectangle(xy=bboxes_coor, outline=CLASS_RGB[labels[i]])
            draw_label.rectangle(xy=[j + 1. for j in bboxes_coor], outline=CLASS_RGB[labels[i]])

            # Text
            text_size = font.getsize(labels[i].upper())
            text_coor = [bboxes_coor[0] + 2., bboxes_coor[1] - text_size[1]]
            textbox_coor = [bboxes_coor[0], bboxes_coor[1] - text_size[1],
                            bboxes_coor[2] + 1., bboxes_coor[1]]
            draw_label.rectangle(xy=textbox_coor, fill=CLASS_RGB[labels[i]])
            draw_label.text(xy=text_coor, text=labels[i].upper(), fill='white', font=font)
        del draw_label

        cv2.imwrite(path, cv2.cvtColor(np.asarray(original_image), cv2.COLOR_RGB2BGR))

        return original_image

def detection_test():
    """
    testing image
    """
    
    image_dir = 'Dataset/img/'
    label_txt = "Dataset/valid_p.txt"

    with open(label_txt) as f:
        lines = f.readlines()

    for line in lines:
        temp_split = line.strip().split()

        # Get the file path
        file_name = temp_split[0]
        folder = file_name.split("/")
        image_path = os.path.join(image_dir, file_name)

        original_image = Image.open(image_path, mode='r')
        original_image = original_image.convert('RGB')
        visualize_detection(original_image, min_score=0.2, max_overlap=0.6, top_k=200,
                            path='Dataset/test/'+folder[0]+'_'+folder[1])

    return visualize_detection

def detection_real():
    """
    detect in real scene
    """
    cap = cv2.VideoCapture(0)
    status = True

    while status:
        retval, frame = cap.read()
        if not(retval):	# if not read frame information
            break  # terminate while loop

        # convert from BGR to RGB
        color_coverted = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)

        # convert from openCV2 to PIL
        pil_image=Image.fromarray(color_coverted)

        pipette_status=visualize_detection(original_image, min_score=0.2, max_overlap=0.6, top_k=200,
                            path='Dataset/test/'+folder[0]+'_'+folder[1])
        
        if bool(pipette_status) == True:
            status = False
            return pipette_status
    
    cap.release()
    cv2.destroyAllWindows()