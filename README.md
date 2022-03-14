# Pull Up RPE

Pull Up RPE is a web app that analyzes how hard you are training on your pull ups. 

It gives you an RPE estimate by calculates your velocity loss from your first few reps compared to your last rep. RPE scores range from 1 - 10, with 1 being really easy and 10 being maximum effort (physically impossible to do another rep).

Pull Up RPE was built with Python, Flask and Javascript. It uses Google's Video Intelligence API to detect your position in a video.

## Links
Live at: https://pulluprpe.herokuapp.com/

Demo video: https://youtu.be/_w7fS19JpJA

My process and code: https://youtu.be/Kzf6FE2zNsE


## Usage

Upload a video of you doing pull ups (from the front, with your face visible). The web app will calculate the amount of repetitions done, the time taken for each rep, the velocity loss and your estimated RPE. It will also display this information as a line graph. 

Make sure to register and set API keys for Google's Video Intelligence API and Imgur's API.

## Possible extensions
1. Analyze RPE for other bodyweight exercises
2. Optimize for mobile to allow for RPE estimates in-between sets
3. Get a custom URL

## How it works
After you upload a video, the video is uploaded to a Google Cloud bucket/folder. Then, that video is passed to the Video Intelligence API to analyze your head position throughout the video. The web app then uses pandas and matplotlib to analyze and graph the data. Lastly, the generated graph is uploaded to Imgur so that it can be displayed back to you. 

