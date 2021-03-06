#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import ntpath
import numpy as np
import math
from scipy import misc
import argparse
import json
import cv2
from sklearn import metrics

from sklearn.decomposition import PCA
import sklearn.metrics.pairwise as pw
import pickle
from tensorpack.tfutils.sesscreate import SessionCreatorAdapter, NewSessionCreator
from tensorflow.python import debug as tf_debug
import uuid
import tensorflow as tf
from tensorpack import *
import lfw
import json

from reader_facenet import *

from face_train_resnet import Model as ResnetModel

from face_train_inception_resnet_v1 import Model as Inception_Resnet_V1_Model


from cfgs.config import cfg


def predict_image_pairs(image1, image2, predict_func, args):
    if args.flage:
        h = 224
        w = 224
    else:
        h = 160
        w = 160
    img1 = misc.imread(image1, mode='RGB')
    img11 = np.fliplr(img1)

    img1 = cv2.resize(img1, (w, h))
    img11 = cv2.resize(img11, (w, h))

    img2 = misc.imread(image2, mode='RGB')
    img22 = np.fliplr(img2)

    img2 = cv2.resize(img2, (w, h))
    img22 = cv2.resize(img22, (w, h))
    
    imgs = []
    imgs.append(img1)
    imgs.append(img11)
    imgs.append(img2)
    imgs.append(img22)
    predict_result = predict_func([imgs])[0]
    dis1 = np.hstack((predict_result[0,:], predict_result[1,:]))
    dis2 = np.hstack((predict_result[2,:], predict_result[3,:]))
 
    cos_dis = 1 - pw.pairwise_distances(np.array([dis1]), np.array([dis2]), metric='cosine')
    return cos_dis

def seek_threshold(rec):
    rec = np.array(rec, dtype=np.float32).reshape(-1,2)

    index1 = np.where(rec[:,1] == 0)
    index2 = np.where(rec[:,1] == 1)

    pos = rec[index1]
    neg = rec[index2]
    max_corr_num = 0
    # for i in range(0.2, 1, 0.001):
    th = 0.01
    while th < 1:
        # print(count)
        count = 0
        pos_idx = np.where(pos[:,0] >= th)
        neg_idx = np.where(neg[:,0] < th)

        pos_corr_num = len(pos_idx[0])
        neg_corr_num = len(neg_idx[0])

        corr_num = pos_corr_num + neg_corr_num

        # print(str(th) + " acuracy: " + str(count) +  " ," +str(float(count / 6000)))
        if corr_num > max_corr_num:
            max_corr_num = corr_num
            print(max_corr_num)
            print(str(th) + " acuracy: " + str(float(max_corr_num / len(rec))) + " " + str(len(rec)) + " pos-accuracy: " + str(pos_corr_num / pos.shape[0]) + " neg-accuracy: " + str(neg_corr_num / neg.shape[0]))

        th += 0.01


def train_validation(rec):
    rec = np.array(rec, dtype=np.float32).reshape(-1,2)

    index1 = np.where(rec[:,1] == 0)
    index2 = np.where(rec[:,1] == 1)

    pos = rec[index1]
    neg = rec[index2]
    max_corr_num = 0
  
    th = 0.01
    while th < 1:
      
        count = 0
        pos_idx = np.where(pos[:,0] >= th)
        neg_idx = np.where(neg[:,0] < th)

        pos_corr_num = len(pos_idx[0])
        neg_corr_num = len(neg_idx[0])

        corr_num = pos_corr_num + neg_corr_num

        if corr_num > max_corr_num:
            max_corr_num = corr_num
            print(max_corr_num)
            print(str(th) + " acuracy: " + str(float(max_corr_num / len(rec))) + " " + str(len(rec)) + " pos-accuracy: " + str(pos_corr_num / pos.shape[0]) + " neg-accuracy: " + str(neg_corr_num / neg.shape[0]))

        th += 0.01

def predict_imags_train_dataset(pos_path, neg_path, predict_func, args):
    with open(pos_path, 'r') as f:
        pos_file = f.readlines()
        print(len(pos_file))

    with open(neg_path, 'r') as f:
        neg_file = f.readlines()
        print(len(neg_file))

   
    flage = []
    is_neg = 0
    for file in [pos_file, neg_file]:
        for item in file:
            imgs_pairs = item.strip().split(' ')
            # image1 = os.path.join(imgs_path, imgs_pairs[0] + ".jpg")
            # image2 = os.path.join(imgs_path, imgs_pairs[1] + ".jpg")
            print(imgs_pairs[0])
            cos_result = predict_image_pairs(imgs_pairs[0], imgs_pairs[1], predict_func, args)[0][0]

            print(cos_result)
            flage.append(cos_result)
            flage.append(is_neg)
        is_neg = 1
   
    train_validation(flage)


def recognition_person(img_path, predict_func, args):

    with open("dataset/person_list.txt", "r") as f:
        file = f.readlines()
    f.close()
    feature =  open("dataset/person_feature.json", "w")
    for item in enumerate(file):
        items = item.strip().split(" ")
        img_path = items[0]
        if args.flage:
            h = 224
            w = 224
        else:
            h = 160
            w = 160
        img1 = misc.imread(img_path, mode='RGB')
        img11 = np.fliplr(img1)

        img1 = cv2.resize(img1, (w, h))
        img11 = cv2.resize(img11, (w, h))

        imgs = []
        imgs.append(img1)
        imgs.append(img11)

        predict_result = predict_func([imgs])[0]
        dis1 = np.hstack((predict_result[0,:], predict_result[1,:]))
        feature.dump({items[0]:dis1})
    feature.close()
##yjf
def get_paths(lfw_dir, pairs):
    nrof_skipped_pairs = 0
    path_list = []
    issame_list = []
    for pair in pairs:
        if len(pair) == 3:
            path0 = os.path.join(lfw_dir, pair[0], pair[0] + '_' + '%04d' % int(pair[1])+'_0.png')
            path1 = os.path.join(lfw_dir, pair[0], pair[0] + '_' + '%04d' % int(pair[2])+'_0.png')
            issame = True
        elif len(pair) == 4:
            path0 = os.path.join(lfw_dir, pair[0], pair[0] + '_' + '%04d' % int(pair[1])+'_0.png')
            path1 = os.path.join(lfw_dir, pair[2], pair[2] + '_' + '%04d' % int(pair[3])+'_0.png')
            issame = False
    
        if os.path.exists(path0) and os.path.exists(path1):    # Only add the pair if both paths exist
            path_list += (path0,path1)
            issame_list.append(issame)
        else:
            nrof_skipped_pairs += 1
    if nrof_skipped_pairs>0:
        print('Skipped %d image pairs' % nrof_skipped_pairs)
    
    return path_list, issame_list##12000, 6000
###yjf
def predict_inception_resnet_v1_structure(lfw_dir, lfw_pairs, predict_func, img_batch_size=100, flage=False):

    pairs = []
    with open(lfw_pairs, 'r') as f:
        for line in f.readlines()[1:]:
            pair = line.strip().split()
            pairs.append(pair)
    
    lfw_paths, actual_issame = get_paths(lfw_dir, np.array(pairs))

    assert (len(lfw_paths) == 12000 and len(actual_issame) == 6000), "validate dataset length not equal"
    assert (len(lfw_paths) % img_batch_size == 0), "img_batch_size error"
    
    img_epochs = len(lfw_paths) // img_batch_size
    img_embeddings = np.zeros((len(lfw_paths), cfg.feature_length))
    for i in range(img_epochs):
        imgs = []
        for line in (lfw_paths[i*img_batch_size : i*img_batch_size+img_batch_size]):
           
            assert (os.path.exists(line)), 'img not exists'
            img = misc.imread(line, mode='RGB')
            if flage == True:
                img = cv2.resize(img, (cfg.image_size, cfg.image_size))
            imgs.append(img)
      
        predict_result = predict_func([imgs])[0]#batch_size * 128
       
        img_embeddings[i*img_batch_size : i*img_batch_size+img_batch_size]=predict_result

    _, _, accuracy, best_threshold, val, val_std, far = lfw.evaluate(img_embeddings, actual_issame, nrof_folds=10)
    print('Best threshold array: ', best_threshold)
    print('Each accuracy: ', accuracy)
    print('Mean thrshold: %2.4f' %  np.mean(best_threshold))
    print('Accuracy: %1.3f+-%1.3f' % (np.mean(accuracy), np.std(accuracy)))
    print('Validation rate: %2.5f+-%2.5f @ FAR=%2.5f' % (val, val_std, far))


def face_recognition_collect_feature(predict_func, imgs_path):
    images = os.listdir(imgs_path)
    features = {}
    facenames = []
    imgs = []
    # for idx, face in enumerate(images):
    #     print(face)
    #     facenames.append(face.split(".")[0])
    #     img = misc.imread(os.path.join(imgs_path, face), mode='RGB')
    #     imgs.append(cv2.resize(img, (160, 160)))
    # print(facenames)
    # predict_result = predict_func([imgs])[0]
    # print(predict_result.shape)
    # for i in range(predict_result.shape[0]):
    #     features[facenames[i]] = predict_result[i].tolist()
    # print(features)
    # result = open("face_feature.json", 'w')
    # result.write(json.dumps(features))


    for idx, face in enumerate(images):
        facenames.append(face.split(".")[0])
        img = misc.imread(os.path.join(imgs_path, face), mode='RGB')
        imgs.append(cv2.resize(img, (160, 160)))
        predict_result = predict_func([imgs])[0]
        features[facenames[idx]] = predict_result[0].tolist()
    print(features)
    result = open("face_feature.json", 'w')
    result.write(json.dumps(features))

    print("over")

 
def face_recognition_realtime(predict_func, video_path):
    assert (os.path.exists(video_path)), 'video_path does not exists'
    cap = cv2.videoCapture(video_path)
    frame_idx = 0
    if cap.isOpened == False:
        cap.open(video_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    videoWrite = cv2.VideoWriter("face_recognition_result.mp4", cv2.VideoWriter_fourcc(*'mp4v'),30,(width, height))

    while cap.isOpened:
        ret, img = cap.read()
        if ret == False:
            break
        

def predict_imags_based_square(pos_path, neg_path, predict_func, args, nrof_folds=10):
    with open(pos_path, 'r') as f:
        pos_file = f.readlines()
        print(len(pos_file))
    is_same_pos = [True for e in range(len(pos_file))]

    with open(neg_path, 'r') as f:
        neg_file = f.readlines()
        print(len(neg_file))
    is_same_neg = [False for e in range(len(neg_file))]

    is_same = is_same_pos + is_same_neg

    imgs_path = 'dataset/alignLfwImage'
    embeddings = []
    for file in [pos_file, neg_file]:
        for item in file:
            imgs_pairs = item.strip().split(' ')
            image1 = os.path.join(imgs_path, imgs_pairs[0] + ".jpg")
            image2 = os.path.join(imgs_path, imgs_pairs[1] + ".jpg")
            print(image2)
            dis1, dis2 = face_validate.predict_image(image1, image2, predict_func, args)
            embeddings.append(dis1)
            embeddings.append(dis2)
    # import pdb
    # pdb.set_trace()
    # embeddings = np.asarray(embeddings, dtype=np.float32)
    # embeddings = np.reshape(embeddings, (len(neg_file)*2*2, len(embeddings[0])))
    # embeddings = tf.nn.l2_normalize(embeddings, 1, 1e-10, name="normalize1")

    for idx, item in enumerate(embeddings):
        maxs = np.max(item)
        mins = np.min(item)
        embeddingsp[idx] = (item - mins) / (maxs - mins)
    # print(len(embeddings))
    # print(embeddings.shape)
    embeddings_1 = embeddings[0::2]
    embeddings_2 = embeddings[1::2]
    print(type(embeddings_2))
    thresholds = np.arange(6000, 23000, 1)
   
 
    tpr, fpr, accuracy = facenet.calculate_roc(thresholds, embeddings_1, embeddings_2, np.asarray(is_same), nrof_folds=nrof_folds)
    print(accuracy)
    print("Accuracy: %1.3f+-%1.3f" % (np.mean(accuracy), np.std(accuracy)))
    auc = metrics.auc(fpr, tpr)
    print("Area Under Curve(auc): %1.3f" % auc)




def predict_imags(pos_path, neg_path, predict_func, args):
    with open(pos_path, 'r') as f:
        pos_file = f.readlines()
        print(len(pos_file))
    with open(neg_path, 'r') as f:
        neg_file = f.readlines()
        print(len(neg_file))

    imgs_path = 'dataset/alignLfwImage'
    cos_results = []
    is_neg = 0
    for file in [pos_file, neg_file]:
        for item in file:
            imgs_pairs = item.strip().split(' ')
            image1 = os.path.join(imgs_path, imgs_pairs[0] + ".jpg")
            image2 = os.path.join(imgs_path, imgs_pairs[1] + ".jpg")
            print(image2)
            cos_result = predict_image_pairs(image1, image2, predict_func, args)[0][0]
            print(cos_result)
            cos_results.append(cos_result)
            cos_results.append(is_neg)
        is_neg = 1
    seek_threshold(cos_results)


def get_pred_func(args):
    sess_init = SaverRestore(args.model_path)
    if args.flage:
        model = ResnetModel(args.depth)    
    else:
        model = Inception_Resnet_V1_Model(False)

    predict_config = PredictConfig(session_init = sess_init,
                                    model = model,
                                    input_names = ["input"],
                                    output_names = ["FEATURE"])
    predict_func = OfflinePredictor(predict_config)
    return predict_func


if __name__ == '__main__':
    parser = argparse.ArgumentParser()


    parser.add_argument('--model_path', default='train_log/facenet_mix_per_image_standardizatio/model-219000')
    parser.add_argument('--video_path', help='video path')
    parser.add_argument('--generate_face_feature', help='aligned face img path')
    parser.add_argument('--flage', action="store_true", help="resnet or inception_resnet_v1 network, true for resnet")
    parser.add_argument('--depth', default='18', type=int, choices=[18, 34, 50, 101])

    parser.add_argument('--lfw_pairs', default='pairs.txt', help="lfw pairs txt")
    parser.add_argument('--lfw_img_batch_size', type=int, default='100')
    parser.add_argument('--lfw_dir', default='/home/user/yjf/facenet_test/dataset_lfw_align_160', help="lfw dir path after align")
    args = parser.parse_args()


    predict_func = get_pred_func(args)
    # if args.video_path != None:
    #     face_recognition_realtime(predict_func, args.video_path)
    if args.generate_face_feature != None:
        face_recognition_collect_feature(predict_func, args.generate_face_feature)
    else:
        predict_inception_resnet_v1_structure(args.lfw_dir, args.lfw_pairs, predict_func, args.lfw_img_batch_size, args.flage)
    

