require 'ec2/amitools/crypto'
require 'ec2/amitools/exception'
require 'ec2/common/http'
require 'ec2/amitools/uploadbundleparameters'
require 'rexml/document'
require 'tempfile'
require 'uri'

NAME = 'ec2-upload-bundle'

#------------------------------------------------------------------------------#

MANUAL =<<TEXT
#{NAME} is a command line tool to upload a bundled Amazon Image to S3 storage 
for use by EC2. An Amazon Image may be one of the following:
- Amazon Machine Image (AMI)
- Amazon Kernel Image (AKI)
- Amazon Ramdisk Image (ARI)

#{NAME} will:
- encrypt the AMI manifest with EC2's public key
- sign the AMI manifest with the user's private key
- create an S3 bucket to store the bundled AMI in if it does not already exist
- upload the AMI manifest and parts files to S3, granting specified privileges 
- on them (defaults to EC2 read privileges)

To manually retry an upload that failed, #{NAME} can optionally:
- skip uploading the manifest
- only upload bundled AMI parts from a specified part onwards
TEXT

BACKOFF_PERIOD = 5

#------------------------------------------------------------------------------#

class MakeBucketError < RuntimeError
  def initialize( bucket, rsp )
    super "Could not create bucket #{bucket}, server response:\n #{rsp}"
  end
end

#------------------------------------------------------------------------------#

class UploadFileError < RuntimeError
  def initialize( file )
    super "Could not upload file: #{file}"
  end
end

#----------------------------------------------------------------------------#

# Upload the specified file.
def upload( s3_url, bucket, file, path, acl, retry_upload, user = nil, pass = nil, debug=false )
  basename = File::basename( file )
  url = "#{s3_url}/#{bucket}/#{basename}"
 
  loop do
    begin
      EC2::Common::HTTP::put( url, path, {"x-amz-acl"=>acl}, user, pass, debug )
      break
    rescue EC2::Common::HTTP::Error::PathInvalid => e
      raise "Error: no such file \"#{path}\""
    rescue RuntimeError => e
      if retry_upload
        STDERR.puts "Failed to upload #{file}, #{e.message}"
        STDOUT.puts "Retrying in #{BACKOFF_PERIOD}s ..."
        sleep BACKOFF_PERIOD
      else
        raise "Error: failed to upload \"#{path}\", #{e.message}"
      end
    end
  end
  
  return url
end

#----------------------------------------------------------------------------#

# Return a list of bundle part filename and part number tuples from the manifest.
def get_part_info( manifest )
  parts = Array.new

  REXML::XPath.each( manifest.root, 'image/parts/part' ) do|part|
    e = REXML::XPath.first(part, 'filename')
    parts << [e.text, part.attribute( 'index' ).to_s.to_i ]
  end
  parts.sort
  parts
end

#------------------------------------------------------------------------------#

def uri2string( uri )
  s = "#{uri.scheme}://#{uri.host}:#{uri.port}#{uri.path}"
  # Remove the trailing '/'.
  return ( s[s.size - 1 ] == 47 ? s.slice( 0..( s.size - 2 ) ) : s )
end

#------------------------------------------------------------------------------#

# Check if the bucket exists and the necessary ACL is set.
def bucket_set?( s3url, bucket, retry_create, user = nil, pass = nil, debug = false )

  path = File.join( s3url, bucket ) + "/?acl"
  
  begin
    response = nil
    options = {'Content-Length' => '0'}
    loop do
      begin
        
        response = EC2::Common::HTTP::get(path, nil, options, user, pass, nil, nil, debug)
        if response.success?
          begin
            STDOUT.puts response.body if debug and response.text?
            doc = REXML::Document.new( response.body )      
            REXML::XPath.each( doc.root, 'AccessControlList/Grant' ) do |grant|
              if ( name = REXML::XPath.first( grant, 'Grantee/DisplayName') and
                   name.text == 'za-team' and
                   permission = REXML::XPath.first( grant, 'Permission' ) and
                   permission.text == 'READ' )
                return true # ACL is set.
              end
            end
          rescue RuntimeError => e
            raise "Could not parse ACL response from server, #{e.message}"
          end
        else
          return false  
        end        
        break
      rescue EC2::Common::HTTP::Error::Retrieve => e
        return false if e.code == 404
        raise e
      rescue StandardError => e # Communication error.
        if retry_create
          STDERR.puts "Failed to access bucket \"#{bucket}\" #{e.message}"
          STDOUT.puts "Retrying in #{BACKOFF_PERIOD}s ..."
          sleep BACKOFF_PERIOD
        else
          raise e
        end
      end
    end
  end
end

#------------------------------------------------------------------------------#

# Create the specified bucket if it does not exist.
def create_bucket( s3url, bucket, acl, retry_create, user = nil, pass = nil, debug=false )  
  begin
    unless bucket_set?( s3url, bucket, retry_create, user, pass, debug )
      STDOUT.puts "Setting bucket ACL to allow EC2 read access ..."
      options = {'Content-Length' => '0'}
      options['x-amz-acl'] = acl if user and pass
      path = File.join( s3url, bucket )
      
      begin
        buffer = Tempfile.new('ec2-create-bucket')      
        loop do
          error = ''
          begin
            rsp = EC2::Common::HTTP::put( path, buffer.path, options, user, pass, debug )
            return true if rsp.success?
            unless retry_create
              STDERR.puts "Could not create or access bucket #{bucket}"
              STDERR.puts "Server response was #{rsp.code} (#{rsp.body})"
              return false
            end
            raise "HTTP PUT returned #{rsp.code}."
          rescue EC2::Common::HTTP::Error::Retrieve => e
            error = ": server response #{e.message} #{e.code}"
          rescue RuntimeError => e
            error = ": error message #{e.message}"
          end
          
          STDERR.puts "Failed to create bucket #{bucket}#{error}"
          STDOUT.puts "Retrying in #{BACKOFF_PERIOD}s ..."
          sleep BACKOFF_PERIOD
        end        
      ensure
        buffer.unlink
      end
    end
  end
end

#------------------------------------------------------------------------------#
  
#
# Get parameters and display help or manual if necessary.
#
def main
  begin
    p = UploadBundleParameters.new( ARGV, NAME )    
  rescue Exception => e
    STDERR.puts e.message
    STDERR.puts "Try '#{NAME} --help'"
    return 1
  end
  
  if p.show_help
    STDOUT.puts p.help
    return 0
  end
  
  if p.manual
    STDOUT.puts MANUAL
    return 0
  end
  
  status = 1
  begin
    # Get the S3 URL.
    s3_uri = URI.parse( p.url )
    s3_url = uri2string( s3_uri )
    retry_upload = p.retry
    
    # Create storage bucket if required.
    create_bucket( s3_url, p.bucket, p.acl, retry_upload, p.user, p.pass, p.debug )
    
    # Load manifest.
    xml = String.new
    manifest_path = p.manifest
    File.open( manifest_path ) { |f| xml << f.read }
    
    # Upload AMI bundle parts.
    STDOUT.puts "Uploading bundled image parts to #{s3_url}/#{p.bucket} ..."
    manifest = REXML::Document.new(xml)
## ROCKS Hack in Threaded Upload. Statically Set to 4. 
    curThread = 0
    maxThreads = 4
    threadComplete = [nil,nil]
    url=[nil,nil]
    tpart_info=[nil,nil]
    tpath=[nil,nil]

    get_part_info( manifest ).each do |part_info|
      if !p.part or ( p.part and part_info[1] >= p.part )

        STDOUT.puts "Uploading #{part_info[0]}."
	# Wait if previous thread in slot curThread is not finished
	if threadComplete[curThread] != nil
		threadComplete[curThread].join
	end

	# record per thread info
        tpath[curThread] = File.join( p.directory, part_info[0] )
	tpart_info[curThread] = part_info[0]

	threadComplete[curThread] = Thread.new { k=curThread; 
		url[k] = upload( s3_url, p.bucket, tpart_info[k], tpath[k], p.acl, retry_upload, p.user, p.pass, p.debug );
		STDOUT.puts "Uploaded #{tpart_info[k]} to #{url[k]}." 
		}
      else
        STDOUT.puts "Skipping #{part_info[0]}."
      end
      curThread += 1
      curThread %= maxThreads
    end

    # Wait for outstanding threads to complete
    for j in 0..(maxThreads -1)
        if threadComplete[j] != nil
                threadComplete[j].join
        end
    end
    
#### ROCKS
    # Encrypt and upload manifest.
    unless p.skipmanifest
      STDOUT.puts "Uploading manifest ..."
      url = upload(s3_url, p.bucket, p.manifest, manifest_path, p.acl, retry_upload, p.user, p.pass, p.debug )
      STDOUT.puts "Uploaded manifest to #{url}."
    else
      STDOUT.puts "Skipping manifest."
    end
    
    status = 0
  rescue EC2::Common::HTTP::Error => e
    STDERR.puts e.message
    status = e.code
  rescue StandardError => e
    STDERR.puts e.message
    STDERR.puts e.backtrace if p.debug
  end  
  
  if status == 0
    STDOUT.puts 'Bundle upload completed.'
  else
    STDOUT.puts 'Bundle upload failed.'
  end
  
  return status
end

#------------------------------------------------------------------------------#
# Script entry point. Execute only if this file is being executed.
if __FILE__ == $0
  begin
    status = main
  rescue Interrupt
    STDERR.puts "\n#{NAME} interrupted."
    status = 255
  end
  exit status
end
