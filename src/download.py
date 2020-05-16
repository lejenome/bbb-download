#!/usr/bin/python3

from xml.dom import minidom
import sys
import os
import shutil
import zipfile
import ffmpeg
import re
import time
from pathlib import Path
from operator import itemgetter

PRESENTATION_PATH = '/var/bigbluebutton/published/presentation/'
RAW_PATH = '/var/bigbluebutton/recording/raw/'
DOWNLOAD_PATH = '/var/log/bigbluebutton/download/'


class Meeting:
    def __init__(self, meetingId):
        tmp = meetingId.split('-')
        if len(tmp) > 2:
            if tmp[2] == 'presentation':
                meetingId = tmp[0] + '-' + tmp[1]
            else:
                sys.exit()
        self.meetingId = meetingId

        presentation_path = Path(PRESENTATION_PATH)
        raw_path = Path(RAW_PATH)
        download_path = Path(DOWNLOAD_PATH)

        self.source_dir = presentation_path / self.meetingId
        self.temp_dir = self.source_dir / 'temp'
        self.target_dir = self.source_dir / 'download'
        self.audio_path = self.temp_dir / 'audio'
        self.events_file = self.source_dir / 'shapes.svg'
        self.log_file = download_path / (self.meetingId + '.log')
        self.source_events = raw_path / self.meetingId / 'events.xml'
        self.deskshare_src_file = self.source_dir / 'deskshare' / 'deskshare.webm'
        self.deskshare_tmp_file = self.temp_dir / 'deskshare.mp4'
        self.events_doc = minidom.parse(self.events_file)

        self.audio_file = self.audio_path + 'audio.ogg'
        self.audio_trimmed = self.temp_dir + 'audio_trimmed.m4a'
        self.result_file = self.target_dir + 'meeting.mp4'
        self.slideshow_file = self.temp_dir + 'slideshow.mp4'

        self.bbb_version = self.get_bbbversion()
        self.process_slides()
        self.apply()

    def apply(self):
        sys.stderr = self.log_file.open('a')
        print("\n<-------------------" + time.strftime("%c") +
              "----------------------->\n",
              file=sys.stderr)
        print("bbb_version: " + self.bbb_version, file=sys.stderr)

    def get_bbbversion(self):
        s_events = minidom.parse(str(self.source_events))
        for event in s_events.getElementsByTagName('recording'):
            bbb_ver = event.getAttribute('bbb_version')
            if bbb_ver:
                return bbb_ver

    def process_slides(self):
        slides = []

        for image in self.events_doc.getElementsByTagName('image'):
            path = image.getAttribute('xlink:href')

            in_times = str(image.getAttribute('in')).split()
            out_times = image.getAttribute('out').split()
            height = int(image.getAttribute('height'))
            width = int(image.getAttribute('width'))

            occurrences = len(in_times)
            for i in range(occurrences):
                # dictionary[float(in_times[i])] = temp_dir + str(path)
                slides.append({
                    'path': str(path),
                    'full_path': self.temp_dir / str(path),
                    'height': height,
                    'width': width,
                    'in': float(in_times[i]),
                    'out': float(out_times[i]),
                })

        slides.sort(key=itemgetter('in'))
        self.slides = slides
        self.total_length = slides[-1]['out']


class MeetingConverter:
    def __init__(self, meeting):
        self.meeting = meeting

    def start(self):
        ffmpeg.set_logfile(str(self.meeting.log_file))
        self.create_slideshow()
        ffmpeg.trim_audio_start(self.meeting.slides[0]['in'],
                                self.meeting.total_length,
                                self.meeting.audio_file,
                                self.meeting.audio_trimmed)
        ffmpeg.mux_slideshow_audio(self.meeting.slideshow_file,
                                   self.meeting.audio_trimmed,
                                   self.meeting.result_file)
        self.serve_webcams()
        # self.zipdir()
        self.copy_mp4()

    def clean(self, clean_all=False):
        print("Cleaning up temp files...", file=sys.stderr)
        if self.meeting.temp_dir.exists():
            shutil.rmtree(str(self.meeting.temp_dir))

        if clean_all and self.meeting.target_dir.exists():
            shutil.rmtree(str(self.meeting.target_dir))

    def create_slideshow(self):
        video_list = self.meeting.source_path / 'video_list.txt'
        f = video_list.open('w')
        ffmpeg.webm_to_mp4(self.meeting.deskshare_src_file,
                           self.meeting.deskshare_tmp_file)
        print("-=create_slideshow=-", file=sys.stderr)
        for i, slide in enumerate(self.meeting.slides):

            tmp_name = '%d.mp4' % i
            tmp_ts_name = '%d.ts' % i
            image = slide['full_path']

            duration = slide['out'] - slide['in']

            out_file = self.meeting.temp_dir / tmp_name
            out_ts_file = self.meeting.temp_dir / tmp_ts_name

            if "deskshare.png" in image:
                print(0, i, slide['in'], duration, file=sys.stderr)
                ffmpeg.trim_video_by_seconds(self.meeting.deskshare_tmp_file,
                                             slide['in'], duration, out_file)
                ffmpeg.mp4_to_ts(out_file, out_ts_file)
            else:
                print(1, i, slide['in'], duration, file=sys.stderr)
                ffmpeg.create_video_from_image(image, duration, out_ts_file)

            f.write('file ' + out_ts_file + '\n')
        f.close()

        ffmpeg.concat_videos(video_list, self.meeting.result_file)
        video_list.unlink()

    def rescale_presentation(self, new_height, new_width):
        for slide in self.meeting.slides:
            ffmpeg.rescale_image(slide['full_path'], new_height, new_width,
                                 slide['full_path'])

    def check_presentation_dims(self):
        height = max([slide['height'] for slide in self.meeting.slides])
        width = max([slide['width'] for slide in self.meeting.slides])

        if height % 2:
            height += 1
        if width % 2:
            width += 1

        self.rescale_presentation(height, width)

    def prepare(self):
        self.meeting.target_dir.mkdir(parents=True, exists_ok=True)
        self.meeting.temp_dir.mkdir(parents=True, exists_ok=True)
        self.meeting.audio_path.mkdir(parents=True, exists_ok=True)

        if not self.meeting.audio_file.exists():
            ffmpeg.extract_audio_from_video(
                self.meeting.source_dir / 'video' / 'webcams.webm',
                self.meeting.audio_file)

        shutil.copytree(
            self.meeting.source_path / 'presentation',
            self.meeting.temp_dir / "presentation",
        )

        self.check_presentation_dims()

    def serve_webcams(self):
        webcams = self.meeting.source_path / 'video' / 'webcams.webm'
        if webcams.exists():
            shutil.copy2(webcams, self.meeting.source_path / 'download')

    def copy_mp4(self):
        if os.path.exists(self.meeting.result_file):
            shutil.copy2(self.meeting.result_file,
                         self.meeting.source_dir / (meetingId + '.mp4'))

    def zipdir(self):
        filename = str(self.meeting.source_dir / (meetingId + '.zip'))
        zipf = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(str(self.meeting.target_dir)):
            for f in files:
                zipf.write(os.path.join(root, f))
        zipf.close()


if __name__ == "__main__":
    tmp = sys.argv[1].split('-')
    try:
        if tmp[2] == 'presentation':
            meetingId = tmp[0] + '-' + tmp[1]
        else:
            sys.exit()
    except IndexError:
        meetingId = sys.argv[1]

    meeting = Meeting(meetingId)
    converter = MeetingConverter(meeting)
    converter.start()
    # converter.clean()
