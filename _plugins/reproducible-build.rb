# Freeze Jekyll's clock to the exact source revision, never checkout mtimes.
# Archives must supply SOURCE_DATE_EPOCH from their validated source Git object.
require 'open3'

Jekyll::Hooks.register :site, :after_reset do |site|
  epoch = ENV['SOURCE_DATE_EPOCH']
  unless epoch
    epoch, status = Open3.capture2('git', '-C', site.source, 'show', '-s', '--format=%ct', 'HEAD')
    raise 'Source Git timestamp unavailable; set SOURCE_DATE_EPOCH for archives' unless status.success?
    epoch = epoch.strip
  end
  unless /\A[0-9]{1,12}\z/.match?(epoch) && Integer(epoch, 10).between?(1, 253402300799)
    raise 'Invalid SOURCE_DATE_EPOCH'
  end

  site.time = Time.at(Integer(epoch, 10)).utc
end
