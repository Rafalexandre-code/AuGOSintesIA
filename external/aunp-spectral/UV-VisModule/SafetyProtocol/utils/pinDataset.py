from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from PIL import Image
from utils.image_process import *
import torchvision.transforms.functional as transform
import torch
import os
import numpy
import cv2 as cv
import random


class pinDataset(Dataset):
    def __init__(self, image_dir, label_txt, image_size=300, training=False, debug=True):
        self.image_size = image_size
        self.paths = []
        self.labels = []
        self.bboxes = []
        self.difficulties = []
        self.training = training
        self.debug = debug

        with open(label_txt) as f:
            lines = f.readlines()

        for line in lines:
            temp_split = line.strip().split()
            file_name = temp_split[0]
            path = os.path.join(image_dir, file_name)

            # Ignore the missing images
            if not os.path.exists(path):
                continue

            self.paths.append(path)

            # Get the bounding boxes info
            num_boxes = (len(temp_split) - 1) // 5
            bbox, label, difficulties = [], [], []

            for i in range(num_boxes):
                x1 = float(temp_split[5 * i + 1])
                y1 = float(temp_split[5 * i + 2])
                x2 = x1 + float(temp_split[5 * i + 3])
                y2 = y1 + float(temp_split[5 * i + 4])
                c = float(temp_split[5 * i + 5])
                bbox.append([x1, y1, x2, y2])
                label.append(c)
                difficulties.append(c)
            self.labels.append(label)
            self.bboxes.append(bbox)
            self.difficulties.append(1)

        self.num_samples = len(self.paths)

    def __getitem__(self, idx):
        image = Image.open(self.paths[idx], mode='r')
        image = image.convert('RGB')
        mean = [0.485, 0.456, 0.406]
        std = [0.229, 0.224, 0.225]

        bboxes = self.bboxes[idx]
        labels = self.labels[idx]
        difficulties = self.difficulties[idx]

        if self.training is True:
            rand_double = random.random()
            if rand_double < 0.4:
                image, bboxes = flip(image, bboxes)
            elif 0.4 <= rand_double <= 0.8:
                image, bboxes, labels = random_crop(image, bboxes, labels)

        if self.debug is True:
            debug_dir = 'tmp/check'
            os.makedirs(debug_dir, exist_ok=True)
            pt1 = (int(bboxes[0][0]), int(bboxes[0][1]))
            pt2 = (int(bboxes[0][2]), int(bboxes[0][3]))
            image2 = numpy.asarray(image)
            cv.rectangle(image2, pt1, pt2, (0, 128, 0), thickness=1)
            cv.imwrite(os.path.join(debug_dir, 'test_{}.jpg'.format(idx)), image2)

        bboxes = torch.FloatTensor(bboxes)
        labels = torch.LongTensor(labels)
        difficulties = torch.ByteTensor(difficulties)

        new_image, new_bboxes = resize(image, bboxes, size=(self.image_size, self.image_size))
        new_image = transform.to_tensor(new_image)
        new_image = transform.normalize(new_image, mean=mean, std=std)

        return new_image, new_bboxes, labels, difficulties

    def __len__(self):
        return self.num_samples

    def collate_fn(self, batch):
        images = list()
        boxes = list()
        labels = list()
        difficulties = list()

        for b in batch:
            images.append(b[0])
            boxes.append(b[1])
            labels.append(b[2])
            difficulties.append(b[3])

        images = torch.stack(images, dim=0)

        return images, boxes, labels, difficulties


def demo():
    image_dir = '../our_dataset/img/'
    label_txt = '../tipStorage.txt'
    dataset = pinDataset(image_dir, label_txt, training=True)
    data_loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0, collate_fn=dataset.collate_fn)

    for i, (images, bboxes, labels, _) in enumerate(data_loader):
        print(images.size(), labels)


if __name__ == '__main__':
    demo()
