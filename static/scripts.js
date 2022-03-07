// Create AJAX object
var ajax = new XMLHttpRequest();

// Global variables 
var video_duration;
var video_file;

// Display video if video_input changes (i.e. file is uploaded)
    // Code from https://stackoverflow.com/questions/63888726/how-to-play-video-from-input-field-in-html?rq=1
document.getElementById("video_input").addEventListener("change", function() {
    // Access file selected in form
    video_file = this.files[0];

    // Create blob URL for video
    var media = URL.createObjectURL(video_file);

    //Update video displayed on website to video uploaded by user
    var video = document.getElementById("video");
    video.src = media;
    video.style.display = "block";

    /* Get video duration after metadata has loaded
        Code from https://stackoverflow.com/questions/2221029/retrieving-html5-video-duration-separately-from-the-file */
    video.addEventListener('loadedmetadata', function() {
        video_duration = video.duration // global variable

        //If video exceeds 120 seconds, show error message and don't upload
        error_message = document.getElementById("error")

        if (video_duration > 120) {
            error_message.style.visibility = "visible"; 
            document.getElementById("error").innerHTML = "ERROR: Video length is over 2 minutes. Please try again after trimming the video length."
        }
        else if (video_duration <= 120) {
            error_message.style.visibility = "hidden";
        }
    });
});

function upload() {
    // Don't let user submit videos over 2 minutes in length, remind them with alert
    if (video_duration > 120) {
        alert("Error: Video over 2 minutes in length")
    }

    //Process video if duration is 120 seconds or under
    else if (video_duration <= 120) {
        // Hide/reset status messages
        document.getElementById("video_uploading").style.visibility = "visible";
        document.getElementById("google_api_wait").style.visibility = "hidden";
        document.getElementById("google_api_done").style.visibility = "hidden";
        document.getElementById("complete").style.visibility = "hidden";
        document.getElementById("error").style.visibility = "hidden";

        // Make AJAX post requests to Flask backend
        // 1. Upload video to Google Cloud
            // jQuery formatting for AJAX request
            // Code from https://stackoverflow.com/questions/59484863/uploading-a-recorded-video-file-using-ajax
        var data = new FormData();
        data.append('video', video_file);
        $.ajax({
            type: "POST",
            enctype: 'multipart/form-data',
            url: "/upload",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            timeout: 60000, //60000 milliseconds = 1 minute
            success: function (response) {
                console.log("File sent to backend server");
                document.getElementById("google_api_wait").style.visibility = "visible";
                // console.log(response)
                var URIvalue = response.gs_URI

                // 2. Send video on Google Cloud to Video Intelligence API for analysis
                    // After receiving gs_URI
                $.ajax({
                    type: "POST",
                    url: "/process",
                    data: {gs_URI: URIvalue},
                        //If just using data: gs_URI, will send gs_URI as key and nothing as value
                    cache: false,
                    timeout: 180000, //180000 milliseconds = 3 minutes

                    success: function (response) {
                        // Update analysis results with AJAX
                        // console.log(response)
                        document.getElementById("reps_done").innerHTML = response.reps_done
                        document.getElementById("rep_concentrics").innerHTML = response.rep_concentrics
                        document.getElementById("rep_negatives").innerHTML = response.rep_negatives
                        document.getElementById("rep_totals").innerHTML = response.rep_totals
                        document.getElementById("rep_speeds").innerHTML = response.rep_speeds
                        document.getElementById("velocity_loss").innerHTML = response.velocity_loss
                        document.getElementById("rpe").innerHTML = response.rpe
            
                        document.getElementById("graph").src = response.image_URL

                        // Show complete status messages
                        console.log("Received results from Google Video API")
                        document.getElementById("google_api_done").style.visibility = "visible"
                        document.getElementById("complete").style.visibility = "visible"

                    },
                    error: function (e) {
                        console.log("ERROR : ", e);
                        document.getElementById("error").innerHTML = "ERROR: Failed to analyze with Google Video Intelligence API."
                        document.getElementById("error").style.visibility = "visible";
                    }
                })

            },
            error: function (e) {
                console.log("ERROR : ", e);
                document.getElementById("error").innerHTML = "ERROR: Could not upload video to Google Cloud.";
                document.getElementById("error").style.visibility = "visible";
            }
        });
    }
}
