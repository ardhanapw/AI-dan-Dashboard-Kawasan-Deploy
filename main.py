import tracemalloc

import numpy as np

import cv2
import supervision as sv
from collections import defaultdict, deque
from inference import InferencePipeline
from inference.core.interfaces.camera.entities import VideoFrame
from datetime import datetime

from inferenceUtils import *

tracemalloc.start()
    
SOURCE_VIDEO_PATH = "rtsp://ksp_explore:initial2023@115.85.94.50:550/ch1/sub/av_stream"
#"rtsp://ksp_explore:initial2023@115.85.94.50:550/ch1/sub/av_stream"
#"D:/PINTU UTAMA CCTV 02 SORE 20-09-2024.MP4"

CONFIDENCE_THRESHOLD = 0.35
IOU_THRESHOLD = 0.5
SPEED_LIMIT = 40 #km/jam

#jalan menuju ke kawasan @4 MP, gate selatan @1 MP

#PINTU-UTAMA-CCTV 01
"""
SOURCE = np.array([
    [542, 644],
    [957, 644],
    [2394, 1204],
    [888, 1269]
])

TARGET_WIDTH = 8.5
#[8.5, 8.5]
TARGET_HEIGHT = 25.5
#[25.5, 25.5]
"""

#PINTU-UTAMA-CCTV 02


SOURCE = np.array([
        [2038, 969],
        [-198, 969],
        [666, 484],
        [1198, 484]
])


SOURCE = np.array([
        [495, 230],
        [-47, 230],
        [158, 115],
        [290, 115]
])

"""
SOURCE = np.array([
        [131*2, 140*2],
        [431*2, 154*2],
        [584*2, 284*2],
        [-76*2, 273*2]
])
"""

TARGET_WIDTH = 19
TARGET_HEIGHT = 51.6


#gerbang selatan
#TARGET_WIDTH = 30
#TARGET_HEIGHT = 32


TARGET = np.array([
    [0, 0],
    [TARGET_WIDTH - 1, 0],
    [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
    [0, TARGET_HEIGHT - 1],
])

view_transformer = ViewTransformer(source=SOURCE, target=TARGET)

csv_tail = getTail(datetime.now())
csv_tail = np.int32(csv_tail)

def GenerateAnnotator(thickness, text_scale, video_info):
      box_annotator_speeding = sv.BoxAnnotator(
          thickness=thickness,
          color=sv.Color.RED
      )
      label_annotator_speeding = sv.LabelAnnotator(
          text_scale=text_scale,
          text_thickness=thickness,
          text_position=sv.Position.TOP_CENTER,
          color=sv.Color.RED
      )
      box_annotator_not_speeding = sv.BoxAnnotator(
          thickness=thickness,
          color=sv.Color.GREEN
      )
      label_annotator_not_speeding = sv.LabelAnnotator(
          text_scale=text_scale,
          text_thickness=thickness,
          text_position=sv.Position.TOP_CENTER,
          color=sv.Color.GREEN
      )
      trace_annotator = sv.TraceAnnotator(
          thickness=thickness,
          trace_length=video_info.fps * 2,
          position=sv.Position.BOTTOM_CENTER
      )

      return box_annotator_speeding, label_annotator_speeding, box_annotator_not_speeding, label_annotator_not_speeding, trace_annotator

"""
false_positive_path = os.getcwd() + '\\' + 'false_positives'
files = os.listdir(false_positive_path)
false_positive_ids = []
"""
bus_truck_tracker_ids = []

def GenerateUtils(source_video_path):
    video_info = sv.VideoInfo.from_video_path(video_path = source_video_path)
    
    byte_track = sv.ByteTrack(
        frame_rate=video_info.fps, track_activation_threshold=CONFIDENCE_THRESHOLD
    )

    thickness = sv.calculate_optimal_line_thickness(
        resolution_wh=video_info.resolution_wh
    )
    
    text_scale = sv.calculate_optimal_text_scale(
        resolution_wh=video_info.resolution_wh
    )
    
    box_annotator_speeding, label_annotator_speeding, box_annotator_not_speeding, label_annotator_not_speeding, trace_annotator = GenerateAnnotator(thickness, text_scale, video_info)
    
    polygon_zone = sv.PolygonZone(
        polygon=SOURCE
    )
    
    coordinates_x = defaultdict(lambda: deque(maxlen=video_info.fps))
    coordinates_y = defaultdict(lambda: deque(maxlen=video_info.fps))
    frame_number = defaultdict(lambda: deque(maxlen=video_info.fps))

    return {'video_info': video_info, 'byte_track': byte_track, 'thickness': thickness, 'text_scale': text_scale, 'box_annotator_speeding': box_annotator_speeding, 
            'label_annotator_speeding': label_annotator_speeding, 'box_annotator_not_speeding': box_annotator_not_speeding ,'label_annotator_not_speeding': label_annotator_not_speeding, 
            'trace_annotator': trace_annotator, 'polygon_zone': polygon_zone, 'coordinates_x': coordinates_x, 'coordinates_y': coordinates_y, 'frame_number': frame_number}

utils = GenerateUtils(SOURCE_VIDEO_PATH)

# open target video
def my_custom_sink(predictions: dict, video_frame: VideoFrame):
    detections = sv.Detections.from_inference(predictions)
    detections = detections[detections.confidence > CONFIDENCE_THRESHOLD]
    detections = detections[utils['polygon_zone'].trigger(detections)]
    detections = detections.with_nms(IOU_THRESHOLD)
    detections = utils['byte_track'].update_with_detections(detections=detections)
    
    #tracker_id di-increment dengan nomor identifikasi paling terbaru (terbesar) di CSV
    detections.tracker_id = np.array([tracker_id + csv_tail for tracker_id in detections.tracker_id])

    points = detections.get_anchors_coordinates(
        anchor=sv.Position.BOTTOM_CENTER
    )
    
    points = view_transformer.transform_points(points=points).astype(int)

    for tracker_id, [_, y] in zip(detections.tracker_id, points):
        utils['frame_number'][tracker_id].append(video_frame.frame_id)
        utils['coordinates_y'][tracker_id].append(y)

    labels = []

    vehicles_speeding = []
    vehicles_not_speeding = []

    annotated_frame = video_frame.image.copy()
    
    for tracker_id in detections.tracker_id:
        ##if detections[detections.tracker_id == tracker_id].class_id[0] == 0 or detections[detections.tracker_id == tracker_id].class_id[0] == 4:    
        #    if tracker_id not in bus_truck_tracker_ids:
        #        saveAnnotatedFrame(detections, tracker_id, annotated_frame)
        #        bus_truck_tracker_ids.append(tracker_id)
        

        if len(utils['frame_number'][tracker_id]) < utils['video_info'].fps / 2:
            labels.append(f"#{tracker_id}")
        else:
            distance = utils['coordinates_y'][tracker_id][-1] - utils['coordinates_y'][tracker_id][0]
            duration = (utils['frame_number'][tracker_id][-1] - utils['frame_number'][tracker_id][0])/25 #FPS
            speed = (distance * 3.6)/duration #m/s ke km/h
            speed = round(speed, 2)

            labels.append({'id': tracker_id, 'label': f" #{tracker_id} {jenisKendaraan(detections, tracker_id)} {abs(int(speed))} km/h"})
            #labels.append({'id': tracker_id, 'label': f"{distance}"})
            
            createRecord(video_frame.frame_timestamp, tracker_id, jenisKendaraan(detections, tracker_id), speed)
            #createCustomRecord(video_frame.frame_timestamp, tracker_id, jenisKendaraan(detections, tracker_id), speed)

            if abs(speed) > SPEED_LIMIT:
                vehicles_speeding.append(tracker_id)
            else:
                vehicles_not_speeding.append(tracker_id)

    annotated_frame = sv.draw_polygon(scene=annotated_frame, polygon=SOURCE, color=sv.Color.RED, thickness=4)
    
    annotated_frame = utils['trace_annotator'].annotate(
        scene=annotated_frame, detections=detections
    )

    for tracker_id in vehicles_speeding:
        selected_labels = [GetDictionaryValue(labels, tracker_id)]
        annotated_frame = utils['box_annotator_speeding'].annotate(
                        scene=annotated_frame, detections=detections[detections.tracker_id == tracker_id]
                        )
        annotated_frame = utils['label_annotator_speeding'].annotate(
                        scene=annotated_frame, detections=detections[detections.tracker_id == tracker_id], labels = selected_labels
                        )

    for tracker_id in vehicles_not_speeding:
        selected_labels = [GetDictionaryValue(labels, tracker_id)]
        annotated_frame = utils['box_annotator_not_speeding'].annotate(
                        scene=annotated_frame, detections=detections[detections.tracker_id == tracker_id]
                        )
        annotated_frame = utils['label_annotator_not_speeding'].annotate(
                        scene=annotated_frame, detections=detections[detections.tracker_id == tracker_id], labels = selected_labels
                        )

    annotated_frame = cv2.resize(annotated_frame, (1280, 720))

    if (video_frame.frame_id) % 125 == 0 and len([item['label'] for item in labels if 'label' in item]) > 0:
        writeAnnotatedFrame(annotated_frame)
        
    cv2.imshow("Predictions", annotated_frame)
    cv2.waitKey(1)


pipeline = InferencePipeline.init(
    model_id= "deteksi-kendaraan-indonesia-4/1",
    api_key = "ebZb1cyYDe2VDxy0A0rH",
    video_reference= SOURCE_VIDEO_PATH,
    on_prediction=my_custom_sink
)

pipeline.start()
pipeline.join()

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno') 

print("[ Top 10 memory-consuming lines ]")
for stat in top_stats[:10]:
    print(stat)
    
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 10**6}MB; Peak: {peak / 10**6}MB")

tracemalloc.stop()






