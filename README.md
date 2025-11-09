# NOPillboxArt
GUI tool used to turn images into in game pillbox pixel images in Nuclear Option

![Screenshot](https://github.com/Synthium0/NOPillboxArt/blob/main/screenshot.png)
## Getting Started
To start, clone this repo by running
```
git clone https://github.com/Synthium0/NOPillboxArt.git
```
Then, cd into it
```
cd NOPillboxArt
```
Ensure Pillow is installed
```
pip3 install Pillow
```
Finally, run the code to begin:
```
python3 main.py
```
## Usage
Import an image by clicking the "Import Art Image" button, and selecting your image in the dialogue.

You can adjust these settings before creating a json mission:
* Threshold: Brightness cutoff for the image 
* Max Pillboxes: Maximum amount of pillboxes to add to the mission
* Spacing: Spacing between each pillbox
* Altitude: Altitude to spawn all pillboxes at

Then, click "Build" to create a json
## NOTE:
This program is ***extremely*** buggy, one notable example is the "Scale Art" feature not being very accurate between the tool size and how it looks in game


