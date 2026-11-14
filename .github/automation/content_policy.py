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
EXAMPLE = re.compile(r'examples/posts/([a-z0-9]+(?:-[a-z0-9]+)*)/[a-z0-9]+(?:-[a-z0-9]+)*\.(py|json)\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
MAX_FILES = 20
MAX_POST = 100_000
MAX_IMAGE = 2_000_000
MAX_EXAMPLE = 20_000
MAX_TOTAL = 8_000_000


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def metadata(pr):
    # Existing editorial PR2 is explicitly outside automation authorization,
    # including any later synchronize/rerun; changing this needs manual review.
    require(type(pr['number']) is int and pr['number'] > 0, 'invalid PR number')
    require(pr['number'] != 2, 'existing PR2 remains manual')
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
        example_match = EXAMPLE.fullmatch(f['filename'])
        require(POST.fullmatch(f['filename']) or IMAGE.fullmatch(f['filename']) or example_match, 'manual-review path')
        if example_match:
            require(any(POST.fullmatch(p) and PurePosixPath(p).stem[11:] == example_match[1] for p in paths),
                    'companion example must accompany its post')


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
    # CommonMark is only an early check. The exact locked Kramdown AST and
    # actual theme output are separately inspected before this gate succeeds.
    require('{:' not in text, 'Kramdown attribute extensions require manual review')
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
    require(set(info) <= {'layout', 'title', 'date', 'categories', 'tags', 'description', 'toc', 'render_with_liquid'}, 'unsafe front matter key')
    if 'render_with_liquid' in info:
        require(info['render_with_liquid'] is False, 'Liquid opt-in forbidden')
    if '{{' in text or '{%' in text:
        require(info.get('render_with_liquid') is False, 'literal Liquid needs render_with_liquid: false')
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
                require(child.type != 'html_inline', 'raw HTML requires manual review')
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


def example(path, data):
    """Passive data or a deliberately tiny arithmetic test language, NOT Python exec.

    No imports/calls/attributes/subscripts/loops/strings/powers. Bounded AST,
    bounded integer arithmetic, and no filesystem/network/process access exist.
    Real Python outside this subset stays manual, even if harmless-looking.
    """
    import ast
    import json
    import operator
    require(EXAMPLE.fullmatch(path) and 0 < len(data) <= MAX_EXAMPLE, 'example path/size')
    text = data.decode('utf-8', errors='strict')
    require(not text.startswith('---') and '<' not in text and '\x00' not in text,
            'example front matter/HTML/control character')
    if path.endswith('.json'):
        # Data-only numeric arrays cannot hide manifests, credentials or policy.
        # Arbitrary objects/strings/templates are manual, not "safe by suffix".
        parsed_data = json.loads(text)
        stack = [(parsed_data, 0)]
        count = 0
        while stack:
            item, depth = stack.pop()
            count += 1
            require(depth <= 12 and count <= 200, 'JSON structure budget')
            if isinstance(item, list):
                stack.extend((child, depth + 1) for child in item)
            else:
                require(type(item) in (int, bool) and abs(item) <= 1_000_000,
                        'only bounded integer/boolean JSON data; other examples need manual review')
        return {'assertions': 0}
    tree = ast.parse(text)
    nodes = list(ast.walk(tree))
    require(len(nodes) <= 200, 'example AST budget')
    env = {}
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                  ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
                  ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
                  ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}
    def value(node, depth=0):
        require(depth <= 12, 'expression depth budget')
        if isinstance(node, ast.Constant):
            result = node.value
        elif isinstance(node, ast.Name):
            require(node.id in env, 'unbound arithmetic name')
            result = env[node.id]
        elif isinstance(node, ast.BinOp):
            require(type(node.op) in operations, 'unsupported arithmetic operator')
            result = operations[type(node.op)](value(node.left, depth + 1), value(node.right, depth + 1))
        elif isinstance(node, ast.Compare):
            require(len(node.ops) == 1 and type(node.ops[0]) in operations, 'unsupported comparison')
            result = operations[type(node.ops[0])](value(node.left, depth + 1), value(node.comparators[0], depth + 1))
        else:
            raise ValueError('manual-review Python construct')
        require(type(result) in (int, bool) and abs(result) <= 1_000_000, 'bounded integers only')
        return result
    assertions = 0
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            require(len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name), 'simple assignment only')
            env[statement.targets[0].id] = value(statement.value)
        elif isinstance(statement, ast.Assert):
            require(statement.msg is None and value(statement.test) is True, 'arithmetic example assertion failed')
            assertions += 1
        else:
            raise ValueError('manual-review Python statement')
    require(assertions > 0, 'Python example needs a bounded assertion')
    return {'assertions': assertions}
