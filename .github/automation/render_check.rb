# frozen_string_literal: true
# Parse with the EXACT locked production renderer, not CommonMark assumptions.
# Stdin is data only: never Liquid-evaluate or Ruby-evaluate article text.
require 'json'
require 'kramdown'
require 'kramdown-parser-gfm'
# JSON escaping may expand source bytes sixfold. Bound transport separately,
# reject overflow explicitly, then enforce the original UTF-8 body budget.
envelope = STDIN.read(600_033)
abort 'Renderer transport budget exceeded' if envelope.bytesize > 600_032
input = JSON.parse(envelope)
body = input.fetch('body')
abort 'Renderer UTF-8 body budget exceeded' unless body.is_a?(String) && body.bytesize <= 100_000
doc = Kramdown::Document.new(body, input: 'GFM', syntax_highlighter: 'rouge')
stack = [doc.root]
until stack.empty?
  node = stack.pop
  abort "Manual review: raw markup #{node.type}" if [:html_element, :xml_comment, :xml_pi, :raw].include?(node.type)
  abort 'Manual review: source attributes' unless node.attr.empty? || [:a, :img, :header, :codeblock].include?(node.type)
  stack.concat(node.children)
end
STDOUT.write(doc.to_html)
