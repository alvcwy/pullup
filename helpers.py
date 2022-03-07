# Helper functions, adapted from code for local files
from google.cloud import videointelligence_v1 as videointelligence # To access Google Video Intelligence API

# Detects people in a video
    # https://cloud.google.com/video-intelligence/docs/people-detection
def detect_person(gcs_uri):

    client = videointelligence.VideoIntelligenceServiceClient()

    # Configure the request
    config = videointelligence.types.PersonDetectionConfig(
        include_bounding_boxes=True,
        include_attributes=True,
        include_pose_landmarks=True,
    )
    context = videointelligence.types.VideoContext(person_detection_config=config)

    # Start the asynchronous request
    operation = client.annotate_video(
        request={
            "features": [videointelligence.Feature.PERSON_DETECTION],
            "input_uri": gcs_uri,
            "video_context": context,
        }
    )

    # print("\nProcessing video for person detection annotations.")
    result = operation.result(timeout=180)

    # print("\nFinished processing.\n")

    # Retrieve the first result, because a single video was processed.
    return result


# Extracts relevant information from results returned by Google Video Intelligence API
def analyze_ts_obj(timestampedObject):
    frames = []
    time_offset = timestampedObject['timeOffset']

    # Remove 's' (seconds) from time_offset, round to 3 decimal places
    timestamp = time_offset[:-1]
    timestamp = round(float(timestamp), 3)

    frame = {'timestamp' : timestamp}
    for landmark in timestampedObject['landmarks']:
        # Track y position of nose, eyes and ears only
            # Other body parts e.g. shoulders, elbows, wrists, hip, knee, ankle not needed
        if landmark['name'] not in ["nose", "left_eye", "right_eye", "left_ear", "right_ear"]:
            continue
        # frame[landmark['name'] + '_x'] = landmark['point']['x']
        # Subtract y value from 1 because positions are calculated from the top left corner
        frame[landmark['name'] + '_y'] = 1 - landmark['point']['y']
    frames.append(frame)
    sorted(frames, key=lambda x: x['timestamp'])
    return frames