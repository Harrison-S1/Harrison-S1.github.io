"""Fail-closed policy shared by read-only validation and trusted orchestration.

Only content validation imports third-party parsers. Metadata policy is stdlib-only.
No article snippets, Liquid, HTML, plugins or PR scripts are ever executed.
"""
import datetime as dt
import io
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urlsplit

REPO = 'Harrison-S1/Harrison-S1.github.io'
AUTHOR = ('Harrison-S1', 54186142)
POST = re.compile(r'_posts/(\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md\Z')
IMAGE = re.compile(r'assets/img/posts/[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*\.(png|jpg|jpeg|webp)\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
MAX_FILES = 20
MAX_POST = 100_000
MAX_IMAGE = 2_000_000
MAX_TOTAL = 8_000_000


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def metadata(pr):
    require(pr['state'] == 'open' and pr['draft'] is False, 'closed/draft PR')
    require((pr['user']['login'], pr['user']['id']) == AUTHOR, 'untrusted author')
    require(pr['base']['ref'] == 'main', 'not main target')
    for side in ('base', 'head'):
        require(pr[side]['repo'] and pr[side]['repo']['full_name'] == REPO, 'fork/incorrect repo')
        require(SHA.fullmatch(pr[side]['sha']), 'invalid SHA')
    require(1 <= pr['changed_files'] <= MAX_FILES, 'file count limit')


def file_policy(files):
    require(1 <= len(files) <= MAX_FILES, 'file count limit')
    paths = [f['filename'] for f in files]
    require(len(paths) == len(set(paths)), 'duplicate paths')
    require(any(POST.fullmatch(p) for p in paths), 'must include a post')
    for f in files:
        require(f['status'] in ('added', 'modified'), 'deletion/rename/type change')
        require(not f.get('previous_filename'), 'rename')
        require(POST.fullmatch(f['filename']) or IMAGE.fullmatch(f['filename']), 'manual-review path')


def link(value):
    """Validate URL syntax only; never network-fetch contributor URLs (SSRF)."""
    require(value and not re.search(r'[\x00-\x20\x7f\\<>]', value), 'unsafe link characters')
    parsed = urlsplit(value)
    if parsed.scheme:
        require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
                'only credential-free HTTPS external links')
        require(not parsed.fragment or '%' not in parsed.fragment, 'encoded external fragment')
    else:
        require(not parsed.netloc and not value.startswith('//'), 'protocol relative URL')
        require(value.startswith(('/', '#')), 'local links must be root-relative or fragments')
        decoded = unquote(parsed.path)
        require('%' not in decoded and '\\' not in decoded and not re.search(r'[\x00-\x20\x7f<>]', decoded),
                'encoded/unsafe local path')
        require('..' not in PurePosixPath(decoded).parts and not parsed.query, 'local traversal/query')
    return value


def post(path, data):
    import yaml
    from markdown_it import MarkdownIt

    require(0 < len(data) <= MAX_POST, 'post size limit')
    text = data.decode('utf-8', errors='strict')
    require(not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', text), 'control character')
    # CommonMark and the locked Kramdown renderer disagree on some code boundaries.
    # Never let a raw HTML opener hide in a CommonMark code token and escape in Jekyll.
    require('<' not in text, 'raw angle opener anywhere requires manual review')
    # No Liquid even in fenced examples: Jekyll processes Liquid before Markdown.
    require(not any(s in text for s in ('{{', '{%', '{:', '<!--', '<?')), 'Liquid/HTML/extensions require manual review')
    require(text.startswith('---\n') and '\n---\n' in text[4:], 'missing front matter')
    front, body = text[4:].split('\n---\n', 1)
    require(len(front) <= 4096, 'front matter size')
    # YAML aliases, tags, anchors and duplicate keys are deliberately unsupported.
    for token in yaml.scan(front):
        require(not isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken, yaml.tokens.TagToken)),
                'YAML alias/anchor/tag')
    node = yaml.compose(front, Loader=yaml.SafeLoader)
    require(isinstance(node, yaml.MappingNode), 'front matter must be mapping')
    keys = [k.value for k, _ in node.value]
    require(len(keys) == len(set(keys)), 'duplicate front matter key')
    info = yaml.safe_load(front)
    require(set(info) <= {'layout', 'title', 'date', 'categories', 'tags', 'description', 'toc'}, 'unsafe front matter key')
    require({'layout', 'title', 'date', 'categories', 'tags'} <= set(info), 'required front matter')
    require(info['layout'] == 'post', 'layout must be post')
    for key in ('title', 'description'):
        if key in info:
            require(isinstance(info[key], str) and 4 <= len(info[key]) <= 240 and
                    not re.search(r'[<>\r\n]', info[key]), 'invalid metadata text')
    if 'toc' in info:
        require(type(info['toc']) is bool, 'toc must be bool')
    match = POST.fullmatch(path)
    require(match, 'invalid post path')
    date = info['date']
    if isinstance(date, str):
        date = dt.datetime.strptime(date, '%Y-%m-%d %H:%M:%S %z')
    require(isinstance(date, dt.datetime) and date.tzinfo is not None, 'date needs time and timezone')
    require(date.date().isoformat() == match[1], 'filename/date mismatch')
    for key in ('categories', 'tags'):
        require(isinstance(info[key], list) and 1 <= len(info[key]) <= 10, 'invalid taxonomy')
        require(all(isinstance(v, str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', v) for v in info[key]),
                'unsafe taxonomy')
    tokens = MarkdownIt('commonmark', {'html': True}).parse(body)
    require(any(t.type == 'heading_open' for t in tokens), 'needs Markdown heading')
    require(sum(len(t.content) for t in tokens if t.type == 'inline') >= 80, 'needs explanatory prose')
    # Kramdown differs from CommonMark. Reject all raw angle brackets in prose,
    # HTML tokens, indented code, and attribute-list extensions, rather than assume sanitization.
    links = []
    for token in tokens:
        require(token.type not in ('html_block', 'code_block'), 'raw HTML/indented code unsupported')
        if token.type == 'fence':
            require(re.fullmatch(r'[a-zA-Z0-9_+-]*', token.info), 'unsafe fence language')
            closing = body.splitlines()[token.map[1] - 1].strip()
            require(closing.startswith(token.markup) and set(closing) <= set(token.markup), 'unclosed fence')
        if token.type == 'inline':
            for child in token.children or []:
                require(child.type not in ('html_inline', 'code_inline'),
                        'raw HTML/inline code requires manual review (renderer disagreement)')
                if child.type == 'text':
                    require('<' not in child.content and '>' not in child.content and
                            not re.search(r'!?\[[^\]]*\]\s*[\[(]', child.content),
                            'raw angle bracket or unresolved Markdown link')
                if child.type in ('link_open', 'image'):
                    links.append(link(child.attrGet('href') if child.type == 'link_open' else child.attrGet('src')))
    return links


def image(path, data):
    from PIL import Image
    import warnings
    require(0 < len(data) <= MAX_IMAGE, 'image size limit')
    expected = {'png': 'PNG', 'jpg': 'JPEG', 'jpeg': 'JPEG', 'webp': 'WEBP'}[path.rsplit('.', 1)[1]]
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        with Image.open(io.BytesIO(data)) as img:
            require(img.format == expected, 'image extension/magic mismatch')
            require(img.width <= 4096 and img.height <= 4096 and img.width * img.height <= 12_000_000,
                    'image dimensions limit')
            require(getattr(img, 'n_frames', 1) == 1, 'animated image')
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()
    return True
