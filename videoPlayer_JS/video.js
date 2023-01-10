let timeoutId = 0;
let timeout2Id = 0;
let timeToShow = 5;
let clickFlag = false;
let sessionFlag = false;
let endFlag = false;

const videoPlayer = document.getElementById("video-player");
function playPause() {
  const video = document.getElementById("video-player");

  let progressBar = document.getElementById("progress");
  const videoTimeAdjusted = video.duration / 0.8;
  const initialSpeed = (2 * progressBar.max) / videoTimeAdjusted + 1;
  const speedRate = initialSpeed / videoTimeAdjusted;
  let updatesPerSecond = 1000 / (initialSpeed - speedRate * video.currentTime);

  if (video.paused) {
    video.play();

    document.getElementById("circle-button").style.display = "none";
    // document.getElementById("play-pause-button-div").style.display = "none";
    // document.getElementById("pause-button-div").style.display = "block";

    animator = function () {
      updatesPerSecond = 1000 / (initialSpeed - speedRate * video.currentTime);
      progressBar.value += 1;
      if (progressBar.value < progressBar.max) {
        timeout2Id = setTimeout(animator, updatesPerSecond);
      }
    };
    timeoutId = setTimeout(animator, updatesPerSecond);
  } else {
    video.pause();
    clearTimeout(timeout2Id);
    clearTimeout(timeoutId);

    document.getElementById("circle-button").style.display = "block";
    // document.getElementById("play-pause-button-div").style.display = "block";
    // document.getElementById("pause-button-div").style.display = "none";
  }
}

function handleAutoPlayClick() {
  clickFlag = true;
  const vid = document.getElementById("video-player");
  vid.currentTime = 0;
  vid.muted = false;
  vid.pause();
  playPause();
  document.getElementById("autoplay-button").style.display = "none";
  document.getElementById("continue-session").style.display = "none";
  document.getElementById("progress-bar-div").style.display = "block";
}

function restartSession() {
  videoPlayer.currentTime = 0;
  document.getElementById("progress").value = 0;
  playPause();
  document.getElementById("progress-bar-div").style.display = "block";
  document.getElementById("continue-session").style.display = "none";
  document.getElementById("end-session").style.display = "none";
  document.getElementById("call-to-action-button-div").style.display = "none";
  endSessionEventListener();
  addCallToActionButtonEventListener();
}

function continueSession() {
  playPause();
  document.getElementById("progress-bar-div").style.display = "block";
  document.getElementById("continue-session").style.display = "none";
  addCallToActionButtonEventListener();
}

function handleVideoClick() {
  playPause();
}

function initializeVideo() {
  videoPlayer.muted = true;
  videoPlayer.play();
  addCallToActionButtonEventListener();
  endSessionEventListener();
}

function addCallToActionButtonEventListener() {
  videoPlayer.addEventListener("timeupdate", function showButton() {
    if ((videoPlayer.currentTime > timeToShow) & clickFlag) {
      document.getElementById("call-to-action-button-div").style.display =
        "block";
      videoPlayer.removeEventListener("timeupdate", showButton);
    }
  });
}

function endSessionEventListener() {
  videoPlayer.addEventListener("ended", function endSession() {
    if (clickFlag) {
      endFlag = true;
      document.getElementById("end-session").style.display = "block";
      document.getElementById("progress-bar-div").style.display = "none";
      // document.getElementById("pause-button-div").style.display = "none";
      videoPlayer.removeEventListener("ended", endSession);
    }
  });
}

videoPlayer.addEventListener("click", function print() {
  clickFlag ? playPause() : handleAutoPlayClick();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && !endFlag) {
    if (clickFlag) {
      document.getElementById("continue-session").style.display = "block";
      document.getElementById("circle-button").style.display = "none";
      // document.getElementById("play-pause-button-div").style.display = "none";
      // document.getElementById("pause-button-div").style.display = "none";
    } else {
      initializeVideo();
    }
  } else {
    if (!videoPlayer.paused) {
      playPause();
    }

    document.getElementById("progress-bar-div").style.display = "none";
    document.getElementById("circle-button").style.display = "none";
    // document.getElementById("play-pause-button-div").style.display = "none";
    // document.getElementById("pause-button-div").style.display = "none";
    document.getElementById("call-to-action-button-div").style.display = "none";
  }
});

// Start player
initializeVideo();
