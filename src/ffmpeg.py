__author__ = 'CreateWebinar.com'

# Python wrapper around the ffmpeg utility
import os
import sys
import shutil
import inspect

FFMPEG = 'ffmpeg'
VID_ENCODER = 'libx264'

logfile = None

def set_logfile(file):
    global logfile
    logfile = file


def ffmpeg(command):
    command = '%s -nostats -hide_banner %s' % (FFMPEG, command)
    fn_name = inspect.stack()[1].function
    print("[CMD:%s] %s" % (fn_name, command), file=sys.stderr)
    if logfile:
        command = '%s 2>> %s' % (command, logfile)
    os.system(command)


def mux_slideshow_audio(video_file, audio_file, out_file):
    ffmpeg('-i %s -i %s -map 0 -map 1 -codec copy -shortest %s' %
           (video_file, audio_file, out_file))


def extract_audio_from_video(video_file, out_file):
    ffmpeg('-i %s -ab 160k -ac 2 -ar 44100 -vn %s' % (video_file, out_file))


def create_video_from_image(image, duration, out_file):
    print("*************** create_video_from_image ******************")
    print(image, "\n", duration, "\n", out_file)
    ffmpeg(
        '-y -loop 1 -r 5 -f image2 -i %s -c:v %s -t %s -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" %s'
        % (image, VID_ENCODER, duration, out_file))


def concat_videos(video_list, out_file):
    ffmpeg('-y -f concat -safe 0 -i %s -c copy %s' % (video_list, out_file))


def mp4_to_ts(input, output):
    ffmpeg('-i %s -c copy -bsf:v h264_mp4toannexb -f mpegts %s' %
           (input, output))


def concat_ts_videos(input, output):
    ffmpeg('-i %s -c copy -bsf:a aac_adtstoasc %s' % (input, output))


def rescale_image(image, height, width, out_file):
    if height < width:
        ffmpeg('-i %s -vf pad=%s:%s:0:oh/2-ih/2 %s -y' %
               (image, width, height, out_file))
    else:
        ffmpeg('-i %s -vf pad=%s:%s:0:ow/2-iw/2 %s -y' %
               (image, width, height, out_file))


def trim_video(video_file, start, end, out_file):
    start_h = start / 3600
    start_m = start / 60 - start_h * 60
    start_s = start % 60

    end_h = end / 3600
    end_m = end / 60 - end_h * 60
    end_s = end % 60

    str1 = '%d:%d:%d' % (start_h, start_m, start_s)
    str2 = '%d:%d:%d' % (end_h, end_m, end_s)
    ffmpeg('-ss %s -t %s -i %s -vcodec copy -acodec copy %s' %
           (str1, str2, video_file, out_file))


def trim_video_by_seconds(video_file, start, end, out_file):
    ffmpeg('-ss %s -i %s -c copy -t %s %s' %
           (start, video_file, end, out_file))


def trim_audio(audio_file, start, end, out_file):
    temp_file = 'temp.mp3'
    start_h = start / 3600
    start_m = start / 60 - start_h * 60
    start_s = start % 60

    end_h = end / 3600
    end_m = end / 60 - end_h * 60
    end_s = end % 60

    str1 = '%d:%d:%d' % (start_h, start_m, start_s)
    str2 = '%d:%d:%d' % (end_h, end_m, end_s)
    ffmpeg('-ss %s -t %s -i %s %s' % (str1, str2, audio_file, temp_file))

    mp3_to_aac(temp_file, out_file)
    os.remove(temp_file)


def trim_audio_start(time, length, full_audio, audio_trimmed):
    trim_audio(full_audio, time, int(length), audio_trimmed)


def mp3_to_aac(mp3_file, aac_file):
    ffmpeg('-y -i %s -c:a aac %s' % (mp3_file, aac_file))


def webm_to_mp4(webm_file, mp4_file):
    ffmpeg('-y -i %s -qscale 0 %s' % (webm_file, mp4_file))


def audio_to_video(audio_file, image_file, video_file):
    ffmpeg(
        '-loop 1 -i %s -i %s -c:v libx264 -tune stillimage -c:a aac -pix_fmt yuv420p -shortest %s'
        % (image_file, audio_file, video_file))
