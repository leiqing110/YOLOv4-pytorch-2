# coding=utf-8
# project
DATA_PATH = "E:\YOLOV4/"
PROJECT_PATH = "E:\YOLOV4/data"
DETECTION_PATH = "E:\YOLOV4/"

MODEL= {"TYPE": ['YOLOv4']}

# train
TRAIN = {
         "DATA_TYPE": 'VOC',
         "TRAIN_IMG_SIZE": 416,
         "AUGMENT": True,
         "BATCH_SIZE": 1,
         "MULTI_SCALE_TRAIN": False,
         "IOU_THRESHOLD_LOSS": 0.5,
         "EPOCHS": 50,
         "NUMBER_WORKERS": 0,
         "MOMENTUM": 0.9,
         "WEIGHT_DECAY": 0.0005,
         "LR_INIT": 1e-4,
         "LR_END": 1e-6,
         "WARMUP_EPOCHS": 2  # or None
         }


# val
VAL = {
        "TEST_IMG_SIZE": 416,
        "BATCH_SIZE": 1,
        "NUMBER_WORKERS": 0,
        "CONF_THRESH": 0.005,
        "NMS_THRESH": 0.45,
        "MULTI_SCALE_VAL": True,
        "FLIP_VAL": True,
        "Visual": True
        }

Customer_DATA = {"NUM": 1, #your dataset number
                 "CLASSES":['aeroplane'],# your dataset class
        }

VOC_DATA = {"NUM": 20, "CLASSES":['aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus',
           'car', 'cat', 'chair', 'cow', 'diningtable', 'dog', 'horse',
           'motorbike', 'person', 'pottedplant', 'sheep', 'sofa',
           'train', 'tvmonitor'],
        }

COCO_DATA = {"NUM":80,"CLASSES":['person',
'bicycle',
'car',
'motorcycle',
'airplane',
'bus',
'train',
'truck',
'boat',
'traffic light',
'fire hydrant',
'stop sign',
'parking meter',
'bench',
'bird',
'cat',
'dog',
'horse',
'sheep',
'cow',
'elephant',
'bear',
'zebra',
'giraffe',
'backpack',
'umbrella',
'handbag',
'tie',
'suitcase',
'frisbee',
'skis',
'snowboard',
'sports ball',
'kite',
'baseball bat',
'baseball glove',
'skateboard',
'surfboard',
'tennis racket',
'bottle',
'wine glass',
'cup',
'fork',
'knife',
'spoon',
'bowl',
'banana',
'apple',
'sandwich',
'orange',
'broccoli',
'carrot',
'hot dog',
'pizza',
'donut',
'cake',
'chair',
'couch',
'potted plant',
'bed',
'dining table',
'toilet',
'tv',
'laptop',
'mouse',
'remote',
'keyboard',
'cell phone',
'microwave',
'oven',
'toaster',
'sink',
'refrigerator',
'book',
'clock',
'vase',
'scissors',
'teddy bear',
'hair drier',
'toothbrush',]}


# model
MODEL = {"ANCHORS":[[(1.25, 1.625), (2.0, 3.75), (4.125, 2.875)],  # Anchors for small obj
            [(1.875, 3.8125), (3.875, 2.8125), (3.6875, 7.4375)],  # Anchors for medium obj
            [(3.625, 2.8125), (4.875, 6.1875), (11.65625, 10.1875)]] ,# Anchors for big obj
         "STRIDES":[8, 16, 32],
         "ANCHORS_PER_SCLAE":3
         }