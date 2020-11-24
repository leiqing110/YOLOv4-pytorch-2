# coding=utf-8
import os
import sys
sys.path.append("..")
sys.path.append("../utils")
import torch
from torch.utils.data import Dataset, DataLoader
from config import cfg
import cv2
import numpy as np
import random
import torchvision.transforms as transforms
import utils.data_augment as dataAug
import utils.tools as tools

def get_image_id(filename):
    return int(os.path.basename(filename).split(".")[0])

class Build_Train_Dataset(Dataset):
    def __init__(self, anno_file, anno_file_type, img_size=416):
        self.img_size = img_size  # For Multi-training
        if cfg.TRAIN.DATA_TYPE == 'VOC':
            self.classes = cfg.VOC_DATA.CLASSES
        elif cfg.TRAIN.DATA_TYPE == 'COCO':
            self.classes = cfg.COCO_DATA.CLASSES
        else:
            self.classes = cfg.DATASET.CLASSES
        self.num_classes = len(self.classes)
        self.class_to_id = dict(zip(self.classes, range(self.num_classes)))
        self.__annotations = self.__load_annotations(anno_file, anno_file_type)
        self.random_crop = dataAug.RandomCrop()
        self.random_flip = dataAug.RandomHorizontalFilp()
        self.random_affine = dataAug.RandomAffine()
        self.resize = dataAug.Resize((self.img_size, self.img_size), True)

    def __len__(self):
        return  len(self.__annotations)

    def __getitem__(self, item):
        assert item <= len(self), 'index range error'

        img_org, bboxes_org = self.__parse_annotation(self.__annotations[item])
        img_org = img_org.transpose(2, 0, 1)  # HWC->CHW
        item_mix = random.randint(0, len(self.__annotations)-1)
        img_mix, bboxes_mix = self.__parse_annotation(self.__annotations[item_mix])
        img_mix = img_mix.transpose(2, 0, 1)

        img, bboxes = dataAug.Mixup()(img_org, bboxes_org, img_mix, bboxes_mix)
        del img_org, bboxes_org, img_mix, bboxes_mix

        label_sbbox, label_mbbox, label_lbbox, sbboxes, mbboxes, lbboxes = self.__creat_label(bboxes)

        img = torch.from_numpy(img).float()
        label_sbbox = torch.from_numpy(label_sbbox).float()
        label_mbbox = torch.from_numpy(label_mbbox).float()
        label_lbbox = torch.from_numpy(label_lbbox).float()
        sbboxes = torch.from_numpy(sbboxes).float()
        mbboxes = torch.from_numpy(mbboxes).float()
        lbboxes = torch.from_numpy(lbboxes).float()

        return img, label_sbbox, label_mbbox, label_lbbox, sbboxes, mbboxes, lbboxes


    def __load_annotations(self, anno_file, anno_type):

        assert anno_type in ['train', 'test'], "You must choice one of the 'train' or 'test' for anno_type parameter"
        with open(os.path.join(cfg.DATA_PATH,anno_file), 'r') as f:
            annotations = list(filter(lambda x:len(x)>0, f.readlines()))
        assert len(annotations)>0, "No images found in {}".format(anno_file)

        return annotations

    def __parse_annotation(self, annotation):
        """
        Data augument.
        :param annotation: Image' path and bboxes' coordinates, categories.
        ex. [image_path xmin,ymin,xmax,ymax,class_ind xmin,ymin,xmax,ymax,class_ind ...]
        :return: Return the enhanced image and bboxes. bbox'shape is [xmin, ymin, xmax, ymax, class_ind]
        """
        anno = annotation.strip().split(' ')

        img_path = os.path.join(cfg.DATA_PATH, anno[0])
        img = cv2.imread(img_path)  # H*W*C and C=BGR
        assert img is not None, 'File Not Found ' + img_path

        bboxes = np.array([list(map(float, box.split(','))) for box in anno[1:]])
        img = dataAug.hsv_aug(img, 0.1, 0.5, 0.5)

        img, bboxes = self.random_flip(np.copy(img), np.copy(bboxes), img_path)
        img, bboxes = self.random_crop(np.copy(img), np.copy(bboxes))
        img, bboxes = self.random_affine(np.copy(img), np.copy(bboxes))
        img, bboxes = self.resize(np.copy(img), np.copy(bboxes))
      
        return img, bboxes

    def __creat_label(self, bboxes):
        """
        Label assignment. For a single picture all GT box bboxes are assigned anchor.
        1、Select a bbox in order, convert its coordinates("xyxy") to "xywh"; and scale bbox'
           xywh by the strides.
        2、Calculate the iou between the each detection layer'anchors and the bbox in turn, and select the largest
            anchor to predict the bbox.If the ious of all detection layers are smaller than 0.3, select the largest
            of all detection layers' anchors to predict the bbox.

        Note :
        1、The same GT may be assigned to multiple anchors. And the anchors may be on the same or different layer.
        2、The total number of bboxes may be more than it is, because the same GT may be assigned to multiple layers
        of detection.

        """

        anchors = np.array(cfg.MODEL.ANCHORS)
        strides = np.array(cfg.MODEL.STRIDES)
        train_output_size = self.img_size / strides
        anchors_per_scale = cfg.MODEL.ANCHORS_PER_SCLAE

        label = [np.zeros((int(train_output_size[i]), 
                           int(train_output_size[i]), 
                           anchors_per_scale, 
                           6+self.num_classes)) for i in range(3)]
        for i in range(3):
            label[i][..., 5] = 1.0

        bboxes_xywh = [np.zeros((150, 4)) for _ in range(3)]   # Darknet the max_num is 30
        bbox_count = np.zeros((3,))

        for bbox in bboxes:
            bbox_coor = bbox[:4]
            bbox_class_ind = int(bbox[4])
            bbox_mix = bbox[5]

            # onehot
            one_hot = np.zeros(self.num_classes, dtype=np.float32)
            one_hot[bbox_class_ind] = 1.0
            one_hot_smooth = dataAug.LabelSmooth()(one_hot, self.num_classes)

            # convert "xyxy" to "xywh"
            bbox_xywh = np.concatenate([(bbox_coor[2:] + bbox_coor[:2]) * 0.5,
                                        bbox_coor[2:] - bbox_coor[:2]], axis=-1)
            # print("bbox_xywh: ", bbox_xywh)

            bbox_xywh_scaled = 1.0 * bbox_xywh[np.newaxis, :] / strides[:, np.newaxis]

            iou = []
            exist_positive = False
            for i in range(3):
                anchors_xywh = np.zeros((anchors_per_scale, 4))
                anchors_xywh[:, 0:2] = np.floor(bbox_xywh_scaled[i, 0:2]).astype(np.int32) + 0.5  # 0.5 for compensation
                anchors_xywh[:, 2:4] = anchors[i]

                iou_scale = tools.iou_xywh_numpy(bbox_xywh_scaled[i][np.newaxis, :], anchors_xywh)
                iou.append(iou_scale)
                iou_mask = iou_scale > 0.3

                if np.any(iou_mask):
                    xind, yind = np.floor(bbox_xywh_scaled[i, 0:2]).astype(np.int32)

                    # Bug : 当多个bbox对应同一个anchor时，默认将该anchor分配给最后一个bbox
                    label[i][yind, xind, iou_mask, 0:4] = bbox_xywh
                    label[i][yind, xind, iou_mask, 4:5] = 1.0
                    label[i][yind, xind, iou_mask, 5:6] = bbox_mix
                    label[i][yind, xind, iou_mask, 6:] = one_hot_smooth

                    bbox_ind = int(bbox_count[i] % 150)  # BUG : 150为一个先验值,内存消耗大
                    bboxes_xywh[i][bbox_ind, :4] = bbox_xywh
                    bbox_count[i] += 1

                    exist_positive = True

            if not exist_positive:
                best_anchor_ind = np.argmax(np.array(iou).reshape(-1), axis=-1)
                best_detect = int(best_anchor_ind / anchors_per_scale)
                best_anchor = int(best_anchor_ind % anchors_per_scale)

                xind, yind = np.floor(bbox_xywh_scaled[best_detect, 0:2]).astype(np.int32)

                label[best_detect][yind, xind, best_anchor, 0:4] = bbox_xywh
                label[best_detect][yind, xind, best_anchor, 4:5] = 1.0
                label[best_detect][yind, xind, best_anchor, 5:6] = bbox_mix
                label[best_detect][yind, xind, best_anchor, 6:] = one_hot_smooth

                bbox_ind = int(bbox_count[best_detect] % 150)
                bboxes_xywh[best_detect][bbox_ind, :4] = bbox_xywh
                bbox_count[best_detect] += 1

        label_sbbox, label_mbbox, label_lbbox = label
        sbboxes, mbboxes, lbboxes = bboxes_xywh

        
        return label_sbbox, label_mbbox, label_lbbox, sbboxes, mbboxes, lbboxes

class Build_VAL_Dataset(Dataset):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        truth = {}
        f = open(os.path.join(cfg.DATA_PATH, cfg.VAL.ANNO_FILE), 'r', encoding='utf-8')
        for line in f.readlines():
            data = line.rstrip().split(" ")
            truth[data[0]] = []
            if len(data) > 1:
                for i in data[1:]:
                    truth[data[0]].append([int(float(j)) for j in i.split(',')])

        self.truth = truth
        self.imgs = list(self.truth.keys())
        
    def get_image_id(filename):
        return int(os.path.basename(filename).split(".")[0])
    
    def __len__(self):
        return len(self.truth.keys())
    
    def __getitem__(self, index):
        img_path = self.imgs[index]
        bboxes_with_cls_id = np.array(self.truth.get(img_path), dtype=np.float)
        
        img = cv2.imread(os.path.join(cfg.DATA_PATH, img_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        num_objs = len(bboxes_with_cls_id)
        target = {}
        # boxes to coco format
        if num_objs > 0:
            boxes = bboxes_with_cls_id[...,:4]
            boxes[..., 2:] = boxes[..., 2:] - boxes[..., :2]  # box width, box height
            target['boxes'] = torch.as_tensor(boxes, dtype=torch.float32)
            target['labels'] = torch.as_tensor(bboxes_with_cls_id[...,-1].flatten(), dtype=torch.int64)
            target['image_id'] = torch.tensor([get_image_id(img_path)])
            target['area'] = (target['boxes'][:,3])*(target['boxes'][:,2])
            target['iscrowd'] = torch.zeros((num_objs,), dtype=torch.int64)
        else:
            target['boxes'] = torch.as_tensor([], dtype=torch.float32)
            target['labels'] = torch.as_tensor([], dtype=torch.int64)
            target['image_id'] = torch.tensor([get_image_id(img_path)])
            target['area'] = torch.as_tensor([], dtype=torch.float32)
            target['iscrowd'] = torch.as_tensor([], dtype=torch.int64)
            
        return img, target

if __name__ == "__main__":

    yolo_dataset = Build_Train_Dataset(cfg.TRAIN.ANNO_FILE,anno_file_type="train", img_size=608)
    dataloader = DataLoader(voc_dataset, shuffle=True, batch_size=1, num_workers=0)

    for i, (img, label_sbbox, label_mbbox, label_lbbox, sbboxes, mbboxes, lbboxes) in enumerate(dataloader):
        if i==0:
            print(img.shape)
            print(label_sbbox.shape)
            print(label_mbbox.shape)
            print(label_lbbox.shape)
            print(sbboxes.shape)
            print(mbboxes.shape)
            print(lbboxes.shape)

            if img.shape[0] == 1:
                labels = np.concatenate([label_sbbox.reshape(-1, 26), label_mbbox.reshape(-1, 26),
                                         label_lbbox.reshape(-1, 26)], axis=0)
                labels_mask = labels[..., 4]>0
                labels = np.concatenate([labels[labels_mask][..., :4], np.argmax(labels[labels_mask][..., 6:],
                                        axis=-1).reshape(-1, 1)], axis=-1)

                print(labels.shape)
                tools.plot_box(labels, img, id=1)
