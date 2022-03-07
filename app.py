import os # To set and access credentials for Google Cloud services
import io # Input/output, writing image bytes for Imgur
import csv # To read and write to csv file
import pandas as pd # Data analysis
import numpy as np # Data analysis
import base64, requests # For uploading image to Imgur
import matplotlib # Creating graph from data
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# So that matplotlib works with Flask
    # Agg backend only writes to files, no GUI component
    # Code from https://stackoverflow.com/questions/49921721/runtimeerror-main-thread-is-not-in-main-loop-with-matplotlib-and-flask

from scipy.signal import argrelextrema # To find maximum and minimum points in data
from google.cloud import storage # For Google Cloud storage
from google.protobuf.json_format import MessageToDict # Convert json to Python dictionary

from flask import Flask, render_template, request, jsonify
from helpers import detect_person, analyze_ts_obj # Helper functions from helpers.py


app = Flask(__name__)

# TODO: Sign up for Google Cloud, Google Video Intelligence and Imgur API services and add your API keys below
    # Credentials for Google Cloud/Video Intelligence API
        # https://console.cloud.google.com/getting-started
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get('YOUR_GOOGLE_CLOUD_CREDENTIALS')

    # Credentials for Imgur API
        # https://imgur.com/account/settings/apps
    client_id = os.environ.get('YOUR_IMGUR_CREDENTIALS')


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    # Read csv file with RPE counts
    with open('rpe_counts.csv', 'r') as f:   
        reader = csv.reader(f)
        counts = next(reader)
    counts = [int(x) for x in counts]

    f.close() # close file
    return render_template("faq.html", counts=counts)

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/upload", methods=["POST"])
def upload():
    # Upload video to Google Cloud bucket
        # Code from https://stackoverflow.com/questions/60843700/direct-to-google-bucket-in-flask
        # https://cloud.google.com/storage/docs/uploading-objects#storage-upload-object-python
    if request.method == 'POST':
        video = request.files.get('video')

        if video:
            try:
                bucket_name = "pullup_rpe"
                video_name = video.filename 
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(video_name) 
                blob.upload_from_file(video)
                video_name = str(video_name)
                gs_URI = "gs://pullup_rpe/{video_name}".format(video_name = video_name)
                # print("Uploaded to Google Cloud")
                return jsonify(success=True, gs_URI=gs_URI)

            except Exception as e:
                return jsonify(message='error_uploading_video'), 500

    return jsonify(message='error_uploading_video'), 500

@app.route("/process", methods=["POST"])
def process():
    if request.method == 'POST':
        gs_URI = request.form.get('gs_URI')
        gs_URI = str(gs_URI)
        # print(gs_URI)

        if gs_URI:
            try:
                # Make request to Google Video Intelligence API
                annotations = detect_person(gs_URI)

                # Convert JSON results from API to dictionary so that data can be processed
                data = MessageToDict(annotations._pb)

                # Extract relevant annotations from data
                people_annotations = data['annotationResults'][0]['personDetectionAnnotations'][0]['tracks'][0]['timestampedObjects']
                
                # Add data to pandas dataframe
                df = pd.DataFrame(analyze_ts_obj(people_annotations[0]))
                for annotation in people_annotations[1:]:
                    result = pd.DataFrame(analyze_ts_obj(annotation))
                    df = pd.concat([df, result])
                
                # Sort dataframe values by timestamp
                df.sort_values('timestamp', ascending=True)
                df.reset_index(drop=True, inplace=True)

                # Calculate average vertical position of nose, eyes and ears
                df['average'] = df[['nose_y','left_eye_y', 'right_eye_y', 'left_ear_y', 'right_ear_y']].mean(axis=1)

                # Drop nose, eyes and ear columns from dataframe (only need average vertical position in calculations)
                df = df.drop('nose_y', axis=1)
                df = df.drop('left_eye_y', axis=1)
                df = df.drop('right_eye_y', axis=1)
                df = df.drop('left_ear_y', axis=1)
                df = df.drop('right_ear_y', axis=1)

                # Plot figure with matplotlib
                figure = plt.figure() # Create figure object
                max_x_axis = float(df['timestamp'].max()) # Find largest timestamp
                x_axis = [i for i in np.arange(0.0, max_x_axis + 1, 1.0)] # Set x-axis to increments of 1s (too crowded if 0.5 secs)
                graph = df.plot('timestamp', ['average'], xticks=x_axis, figsize=(20, 5)) # Plot graph
                graph.get_legend().remove() # Remove legend from graph
                graph.set_xlabel("Time (s)") 
                graph.set_ylabel("Vertical position")
                plt.title("Average Vertical Position Over Time")

                # Determine local maxima and minima for start and end of each repetition
                n = 7  # Number of points to be checked before and after (arbitrary value, can adjust for higher accuracy)
                df['max'] = df.iloc[argrelextrema(df.average.values, np.greater_equal, order=n)[0]]['average']
                df['min'] = df.iloc[argrelextrema(df.average.values, np.less_equal, order=n)[0]]['average']
                plt.scatter(df['timestamp'], df['min'], c='r')
                plt.scatter(df['timestamp'], df['max'], c='g')

                # Upload matplotlib graph to Imgur, use png hosted on Imgur to display on website
                    # Code from https://gist.github.com/ikmckenz/de1c68f7293e998e38b6c7b92ec36b19
                    # typo in code above: import base64, not 46
                pic_bytes = io.BytesIO()
                plt.savefig(pic_bytes, format='png', bbox_inches='tight')
                pic_bytes.seek(0)
                pic_string = base64.b64encode(pic_bytes.getvalue())
                url = 'https://api.imgur.com/3/upload.json'
                imgur_id = "Client-ID %s" % client_id
                headers = {"Authorization": imgur_id}
                resp = requests.post(url,
                                    headers=headers,
                                    data={
                                        'image': pic_string,
                                        'type': 'base64'
                                    })
                resp = resp.json()
                image_URL = resp['data']['link']
                # print(image_URL)

                # Extract previously found minima and maxima and add to new dataframe for easier access 
                minimum_rows = df[df['min'].notnull()] # Extract rows where 'min' column is not null (i.e. all minimum points)
                minimum_timestamps = minimum_rows['timestamp'].tolist() # Add timestamps to list
                maximum_rows = df[df['max'].notnull()]
                maximum_timestamps = maximum_rows['timestamp'].tolist()
                max_and_min = pd.concat([minimum_rows, maximum_rows])
                max_and_min = max_and_min.sort_values('timestamp', ascending=True)

                # Calculate repetitions, rep times, and rep speeds using dataframe created above
                reps = df['max'].count() # Counts non NaN values in max column i.e. amount of reps
                rep_concentrics = []
                rep_negatives = []
                rep_times = []
                rep_speeds = [] # speed = position change / time
                current_min_time = -1
                current_max_time = -1
                current_min_position = -1
                current_max_position = -1
                prev_min = False # to track if previous point was a minimum or not
                prev_max = False # to track if previous point was a maximum or not
                for index, row in max_and_min.iterrows():
                    if pd.notnull(row['min']): # if measurement is for minimum point
                        next_min_time = float(row['timestamp'])
                        if current_min_time != -1 and prev_min == False: # if already found minimum point previously
                            rep_time = next_min_time - current_min_time
                            rep_times.append(round(rep_time, 1))
                        current_min_time = next_min_time
                        if current_max_time != -1: # if already found maximum point previously
                            rep_negative = current_min_time - current_max_time
                            rep_negatives.append(round(rep_negative, 1))
                        current_min_position = row['average'] # update min position
                        prev_min = True
                        prev_max = False
                    if pd.notnull(row['max']) and current_min_time != -1: # if maximum point and minimum point before exists
                        current_max_time = float(row['timestamp'])
                        if prev_max == False: # skip below code if previous point was a maximum
                            rep_concentric = current_max_time - current_min_time
                            rep_concentrics.append(round(rep_concentric, 1))
                            current_max_position = row['average']
                            position_change = current_max_position - current_min_position
                            rep_speed = 100 * (position_change / rep_concentric) # multiply by 100 for easier comparison
                            rep_speeds.append(round(rep_speed, 1))
                        elif prev_max == True:
                            reps -= 1
                        prev_min = False
                        prev_max = True
                    elif pd.notnull(row['max']) and current_min_time == -1: # if first point found is maximum
                        reps -= 1


                # Calculate velocity loss    
                if len(rep_speeds) < 3: # to avoid keyValue error if user does less than 3 pull ups
                    starting_velocity = rep_speeds[1]
                else:
                    starting_velocity = (rep_speeds[0] + rep_speeds[1] + rep_speeds[2]) / 3
                ending_velocity = rep_speeds[-1]
                velocity_loss_percentage = ((ending_velocity - starting_velocity) / starting_velocity) * 100
                velocity_loss_percentage = round(velocity_loss_percentage, 1)

                # Calculate corresponding RPE and update rpe_counts csv file
                # Read csv file with RPE counts
                with open('rpe_counts.csv', 'r') as f:   
                    reader = csv.reader(f)
                    counts = next(reader)
                f.close() # close file
                # print(counts)

                counts = [int(x) for x in counts]
                if velocity_loss_percentage > -12:
                    rpe = "6 - 7"
                    counts[0] += 1
                elif velocity_loss_percentage > -20:
                    rpe = "7 - 7.5"
                    counts[1] += 1
                elif velocity_loss_percentage > -25:
                    rpe = "7.5 - 8"
                    counts[1] += 1
                elif velocity_loss_percentage > -30:
                    rpe = "8 - 9"
                    counts[2] += 1
                elif velocity_loss_percentage > -35:
                    rpe = "Yeah buddy! (9 - 9.5)"
                    counts[3] += 1
                elif velocity_loss_percentage <= -35:
                    rpe = "Lightweight baby! (9.5 - 10)"
                    counts[4] += 1

                with open('rpe_counts.csv', 'w') as f:
                    writer = csv.writer(f)
                    writer.writerow(counts)
                f.close()
                # print(counts)

                # Reformat results to pass back as JSON
                    # Change everything to strings for better formatting when displaying results
                velocity_loss = str(velocity_loss_percentage) + "%"
                reps = str(reps)
                # Change every element from float to string, then join them together as a single string
                rep_concentrics = ", ".join([str(x) for x in rep_concentrics])
                rep_negatives = ", ".join([str(x) for x in rep_negatives])
                rep_times = ", ".join([str(x) for x in rep_times])
                rep_speeds = ", ".join([str(x) for x in rep_speeds])

                return jsonify (
                    success=True, 
                    reps_done=reps,
                    rep_concentrics=rep_concentrics,
                    rep_negatives=rep_negatives,
                    rep_totals=rep_times,
                    rep_speeds=rep_speeds,
                    velocity_loss=velocity_loss,
                    rpe=rpe,
                    image_URL=image_URL
                )
            except Exception as e:
                # print("error with analyzing results")
                return jsonify(message='error_analyzing_video'), 500

    return jsonify(message='error_analyzing_video'), 500