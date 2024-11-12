import cv2
import os
import numpy as np
from PIL import Image
import csv
import pandas as pd

class ViewTransformer:
    def __init__(self, source: np.ndarray, target: np.ndarray) -> None:
        source = source.astype(np.float32)
        target = target.astype(np.float32)
        self.m = cv2.getPerspectiveTransform(source, target)

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        if points.size == 0:
            return points

        reshaped_points = points.reshape(-1, 1, 2).astype(np.float32)
        transformed_points = cv2.perspectiveTransform(reshaped_points, self.m)
        return transformed_points.reshape(-1, 2)

def GetDictionaryValue(dictionary, id):
    for item in dictionary:
      if(type(item) == dict) and (item.get('id') == id):
          return item.get('label')

def jenisKendaraan(detections, id):
    classes = ['bis', 'mobil', 'motor', 'truk']
    detection_class = int(detections[detections.tracker_id == id].class_id)
    return classes[detection_class]

def calculateDistance(x1, y1, x2, y2):
    multiplying_factor = -1
    if y2-y1 < 0:
        multiplying_factor = 1

    x = (x2-x1)**2
    y = (y2-y1)**2
    distance = (x+y)**(1/2)
    return distance * multiplying_factor

def writeAnnotatedFrame(annotated_frame):
    annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(annotated_frame_rgb)
    path = os.getcwd() + '\\' + 'inference_result'
    if not os.path.exists(path):
        os.makedirs(path)
    image_pil.save(f"{path}\current_frame.jpg")

def saveAnnotatedFrame(detections, id, annotated_frame):
    #bbox_area = detections[detections.tracker_id == id].xyxy[0]
    annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    
    classes = ['bis', 'mobil', 'motor', 'truk']
    detection_class = int(detections[detections.tracker_id == id].class_id)
    
    path = os.getcwd() + '\\' + classes[detection_class]
    jenis_kendaraan = classes[detection_class]
    
    img = Image.fromarray(annotated_frame_rgb)
    #img = img.crop((bbox_area[0], bbox_area[1], bbox_area[2], bbox_area[3]))
    img.save(f"{path}/{jenis_kendaraan}_{id}.jpg")

"""
def checkforFalsePositive(jenis_kendaraan, tracker_id, video_frame):
    annotated_frame = video_frame.image.copy()
    annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(annotated_frame_rgb)
    target_path = os.getcwd() + '\\' + 'false_positives_03_09_24_sore_frames'
    
    frame_id = video_frame.frame_id
    
    source_filename = jenis_kendaraan + '_' + str(tracker_id) + '.jpg'
    if source_filename in files and tracker_id not in false_positive_ids:
        false_positive_ids.append(tracker_id)
        img.save(f"{target_path}/frame{frame_id}_id{tracker_id}_{jenis_kendaraan}.jpg")
"""

def saveFrameContaining(detections, video_frame): #save frame containing bus and truck
    annotated_frame = video_frame.image.copy()
    annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(annotated_frame_rgb)
    
    frame_id = video_frame.frame_id
    vehicles_detected = detections.class_id
    path = os.getcwd() + '\\' + 'frames'
    
    if 0 in vehicles_detected:
        jenis_kendaraan = 'bis'
        img.save(f"{path}/{frame_id}_{jenis_kendaraan}.jpg")
    elif 4 in  vehicles_detected:
        jenis_kendaraan = 'truk'
        img.save(f"{path}/{frame_id}_{jenis_kendaraan}.jpg")

def reformatDate(date):
    year = int(date[:4])
    month = int(date[5:7])
    day = int(date[8:10])
    
    """
    if date.date().month < 10:
        month = '0' + month
    if date.date().day < 10:
        day = '0' + day
    """
    
    return year * 10000 + month * 100 + day

def createRecordDirectory(all_vehicle_record_path, monthly_vehicle_record_path, record_name):
    if not os.path.exists(all_vehicle_record_path):
        os.makedirs(all_vehicle_record_path)
    
    if not os.path.exists(monthly_vehicle_record_path):
        os.makedirs(monthly_vehicle_record_path)
        
    return monthly_vehicle_record_path + '\\' + record_name

def writeRecord(record_path, timestamp, id, jenis_kendaraan, kecepatan):
    #Jika tidak ada floating point
    if len(str(timestamp)) == 19:
        timestamp = str(timestamp) + '.000001'

    if not os.path.isfile(record_path):
        with open(record_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['waktu_terekam', 'nomor_identifikasi', 'jenis_kendaraan', 'kecepatan'])
            
    with open(record_path, 'a', newline='') as csvfile:
        data = [{'waktu_terekam': timestamp, 'nomor_identifikasi': id, 'jenis_kendaraan': jenis_kendaraan, 'kecepatan': kecepatan}]
        fieldnames = ['waktu_terekam', 'nomor_identifikasi', 'jenis_kendaraan', 'kecepatan']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerows(data)

def modifyRecord():
    all_vehicle_record_path = os.getcwd() + '\\' + 'vehicle_records'
    file_path = all_vehicle_record_path + '\\' + '9-2024' + '\\' + '8-9-2024.csv'
    
    df = pd.read_csv(file_path)
    df['nomor_identifikasi'] = df['nomor_identifikasi'].map('20240908{}'.format)
    df.to_csv(file_path, index=False)

def createDirectoryVariable(timestamp):
    current_date = str(timestamp)[:10]
    all_vehicle_record_path = os.getcwd() + '\\' + 'vehicle_records'
    monthly_vehicle_record_path = all_vehicle_record_path + '\\' + '-'.join([str(int(current_date[5:7])), current_date[:4]])

    return current_date, all_vehicle_record_path, monthly_vehicle_record_path

def createRecord(timestamp, id ,jenis_kendaraan, kecepatan):
    current_date, all_vehicle_record_path, monthly_vehicle_record_path = createDirectoryVariable(timestamp)
    record_name = '-'.join([str(int(current_date[8:10])), str(int(current_date[5:7])), current_date[:4]]) + '.csv'
    date_for_id = reformatDate(current_date) * 1000000
    id = date_for_id + id
    
    record_path = createRecordDirectory(all_vehicle_record_path, monthly_vehicle_record_path, record_name)
    writeRecord(record_path, timestamp, id, jenis_kendaraan, kecepatan)

def createCustomRecord(timestamp, id ,jenis_kendaraan, kecepatan):
    current_date, all_vehicle_record_path, monthly_vehicle_record_path = createDirectoryVariable(timestamp)
    record_name = 'custom.csv'
    date_for_id = reformatDate(current_date) * 1000000
    id = date_for_id + id
        
    record_path = createRecordDirectory(all_vehicle_record_path, monthly_vehicle_record_path, record_name)
    writeRecord(record_path, timestamp, id, jenis_kendaraan, kecepatan)

def getTail(timestamp):
    current_date, all_vehicle_record_path, monthly_vehicle_record_path = createDirectoryVariable(timestamp)
    record_name = '-'.join([str(int(current_date[8:10])), str(int(current_date[5:7])), current_date[:4]]) + '.csv'
    record_path = createRecordDirectory(all_vehicle_record_path, monthly_vehicle_record_path, record_name)

    if not os.path.isfile(record_path):
        return int(0)

    df = pd.read_csv(record_path)
    tail = df['nomor_identifikasi'].max()
    tail -= reformatDate(current_date) * 1000000
    return tail

#print(getTail('2024-09-20 12:35:15.955979'))