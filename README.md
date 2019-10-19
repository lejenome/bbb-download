# bbb-download

A python script that produces downloadable material for existing and new recordings for your BigBlueButton server.
Final MP4 video will include only webcams, audio and screenshares (no presentation, no chat window, no whiteboard).
- BigBlueButton 2.0 is supported (10.08.2018)
- Screenshare supported (18.09.2018)
- BigBlueButton 2.2 is supported (tested with BBB 2.2 beta 8)

## Requirements
1. python2.7
2. ffmpeg compiled with libx264 support (included)
3. Installed and configured Big Blue Button server (1.1 or 2.0+)

## Installation (need to be root)
```
git clone https://github.com/ruess/bbb-download.git
cd bbb-download
chmod u+x install.sh
sed -i -e 's/\r$//' install.sh
sudo ./install.sh

```


This copies the download scripts to the BigBlueButton scripts folder, and copies compiled FFMPEG to the /opt/ffmpeg folder.
It also installs python2.7 and additional libs and give an appropriate rights for MP4 files to make them available for download.

NOTE: You may use the guide [here](https://trac.ffmpeg.org/wiki/CompilationGuide/Ubuntu) to compile ffmpeg in Ubuntu by your own. Be sure to include the following flags.
```
--enable-version3 --enable-postproc --enable-libvorbis --enable-libvpx --enable-libx264 --enable-libmp3lame --enable-libfdk-aac --enable-gpl --enable-nonfree''
```

## Usage
After running the installation script (install.sh), the python script that produces the downloadable material, will be called for each recording automatically by the BigBlueButton monitoring scripts, after each recording has been transcoded and published.

## Outputs
Final MP4 video will include only presentation, audio and screenshare (no chat window, no whiteboard).

Link to download MP4 file will look like this: https://yourBBBserverURL/download/presentation/{meetingID}/{meetingID}.mp4
If your BigBlueButton server is connected to https://createwebinar.com contol panel, all webinar participants will be able to download the recorded webinars from the website in one click.

## Setup Automatic Upload of MP4 Recording to Youtube Channel
1. Login to https://console.developers.google.com and create a new project
2. Enable the Google Youtube API from your developer console (version 3 as of this writing)
3. Go to OAuth consent screen and configure according to your preferences
4. Go to Credentials screen, click Create Credentials button and select OAuth client ID
5. Choose "Other" for credential type and give it a name, then click Create. A dialogue box will appear with your new client ID and client secret keys.
6. Next, go back to your server terminal and do the following:
```
cp ~/bbb-download/src/client_secrets.json /usr/local/bigbluebutton/core/scripts/post_publish/
```

7. Now edit file client_secrets.json in /usr/local/bigbluebutton/core/scripts/post_publish/ using the client ID and client secret from step 5

8. Run:
```
chown bigbluebutton:bigbluebutton /usr/local/bigbluebutton/core/scripts/post_publish/*.json
```
9. Run:
```
/usr/bin/python /usr/local/bigbluebutton/core/scripts/post_publish/upload.py
```
 -> this will return a long URL. Copy and paste the URL into your browser, go through the Google Authorization process, then copy and paste the code it returns back into your terminal.

10. Check that files client_secret.json and upload.py are in both in "/usr/local/bigbluebutton/core/scripts/post_publish/"

11. Run:
```
chown bigbluebutton:bigbluebutton /usr/local/bigbluebutton/core/scripts/post_publish/*.json
```
. . . once again.

NOTES:
1. At this point, all new mp4 recordings will automatically be uploaded to the Youtube channel that you selected during the authorization process. Processing and upload time can take up to an hour depending on recording length plus your server performance profile and your upload capacity.

2. To re-upload any current videos on your youtube channel, delete the file reference in /var/bigbluebutton/recording/status/youtube/#{meeting_id}-youtube.done
