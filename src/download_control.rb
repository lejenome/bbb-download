#!/usr/bin/ruby
# encoding: UTF-8

require "trollop"
require File.expand_path('../../../lib/recordandplayback', __FILE__)

logger = Logger.new("/var/log/bigbluebutton/post_publish.log", 'weekly' )
logger.level = Logger::INFO
BigBlueButton.logger = logger

opts = Trollop::options do
  opt :meeting_id, "Meeting id to archive", :type => String
end
meeting_id = opts[:meeting_id]

published_files = "/var/bigbluebutton/published/presentation/#{meeting_id}"
meeting_metadata = BigBlueButton::Events.get_meeting_metadata("/var/bigbluebutton/recording/raw/#{meeting_id}/events.xml")

#
# This runs the download script
#
BigBlueButton.logger.info("Recording download video generation for [#{meeting_id}] starts")

begin
  callback_url = meeting_metadata.key?("bbb-download-ready-url") ? meeting_metadata["bbb-download-ready-url"].value : nil

  unless callback_url.nil?
    download_status = system("/usr/bin/python3 /usr/local/bigbluebutton/core/scripts/post_publish/download.py #{meeting_id}")
  end

  unless callback_url.nil?
    props = JavaProperties::Properties.new("/usr/share/bbb-web/WEB-INF/classes/bigbluebutton.properties")
    secret = props[:securitySalt]
    external_meeting_id = meeting_metadata["meetingId"].value

    payload = { meeting_id: external_meeting_id, record_id: meeting_id }
    payload_encoded = JWT.encode(payload, secret)

    uri = URI.parse(callback_url)
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == 'https')

    BigBlueButton.logger.info("Sending request to #{uri.scheme}://#{uri.host}#{uri.request_uri}")
    request = Net::HTTP::Post.new(uri.request_uri)
    request.set_form_data({ signed_parameters: payload_encoded })

    response = http.request(request)
    code = response.code.to_i

    if code == 410
      BigBlueButton.logger.info("Notified for deleted meeting: #{meeting_id}")
      # TODO: should we automatically delete the recording here?
    elsif code == 404
      BigBlueButton.logger.info("404 error when notifying for recording: #{meeting_id}, ignoring")
    elsif code < 200 || code >= 300
      BigBlueButton.logger.info("Callback HTTP request failed: #{response.code} #{response.message} (code #{code})")
    else
      BigBlueButton.logger.info("Recording notifier successful: #{meeting_id} (code #{code})")
    end
  end

rescue => e
  BigBlueButton.logger.info("Rescued")
  BigBlueButton.logger.info(e.to_s)
end

BigBlueButton.logger.info("Download video ready notify ends")

exit 0
