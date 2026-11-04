"""Read-only Git object validation, trusted-base overlay, and built local-link checks."""
import argparse
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
from urllib.parse import unquote, urlsplit

import content_policy as policy


def git(*args):
    return subprocess.check_output(['git', *args], timeout=60)


def check_entry(mode, typ, size, path):
    policy.require(mode == '100644' and typ == 'blob', 'symlink/executable/non-blob')
    limit = policy.MAX_POST if policy.POST.fullmatch(path) else (
        policy.MAX_EXAMPLE if policy.EXAMPLE.fullmatch(path) else policy.MAX_IMAGE)
    policy.require(0 < size <= limit, 'blob size limit')


class IDs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == 'id' or (tag == 'a' and key == 'name'):
                self.ids.add(value)


def check_links(root, page, links):
    root = root.resolve()
    for value in links:
        policy.link(value)
        url = urlsplit(value)
        if url.scheme == 'https':
            continue
        target = root / unquote(url.path or page).lstrip('/')
        if target.is_dir():
            target = target / 'index.html'
        policy.require(target.resolve().is_relative_to(root) and target.is_file(), 'broken local link: ' + value)
        if url.fragment:
            policy.require(target.suffix == '.html', 'fragment on non-HTML asset')
            parser = IDs()
            parser.feed(target.read_text(encoding='utf-8'))
            policy.require(unquote(url.fragment) in parser.ids, 'broken fragment: ' + value)


class Article(HTMLParser):
    """Inspect actual Jekyll/Kramdown output, not just CommonMark's interpretation.

    Chirpy7 has one exact content div; post-content remains the isolated fragment
    test wrapper. Exact Kramdown AST checking rejects raw HTML BEFORE Jekyll, so
    contributor markup cannot close the wrapper to evade output inspection.
    Theme upgrades that change this contract fail closed and need review.
    """
    TAGS = set('div span p a img h1 h2 h3 h4 h5 h6 ul ol li blockquote hr br pre code '
               'em strong del s table thead tbody tr td th i button'.split())
    ATTRS = set('loading class id href src data-src alt title width height type role tabindex '
                'aria-label aria-hidden data-title data-lang data-toggle data-placement '
                'data-clipboard-text data-proofer-ignore data-label-text data-title-succeed'.split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.wrappers = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        # Chirpy also uses post-content among multiple classes in its search UI.
        # The article wrapper's class value is exactly post-content.
        if tag == 'div' and dict(attrs).get('class') in ('post-content', 'content'):
            policy.require(self.depth == 0, 'nested article wrapper')
            self.wrappers += 1
            self.depth = 1
        elif self.depth and tag == 'div':
            self.depth += 1
        if not self.depth:
            return
        policy.require(tag in self.TAGS, 'unsafe rendered article element: ' + tag)
        policy.require(len(attrs) == len(set(k for k, _ in attrs)), 'duplicate rendered attribute')
        for key, value in attrs:
            policy.require(key in self.ATTRS, 'unsafe rendered article attribute: ' + key)
            if key in ('href', 'src', 'data-src'):
                self.links.append(policy.link(value))

    def handle_endtag(self, tag):
        if self.depth and tag == 'div':
            self.depth -= 1


def rendered_article(html):
    parser = Article()
    parser.feed(html)
    parser.close()
    policy.require(parser.wrappers == 1 and parser.depth == 0, 'missing/ambiguous/unclosed article wrapper')
    return parser.links


def check_slugs(paths, changed):
    for path in changed:
        if policy.POST.fullmatch(path):
            slug = Path(path).stem[11:].lower()
            matches = [p for p in paths if p.startswith('_posts/') and
                       Path(p).stem[11:].lower() == slug]
            policy.require(matches == [path], 'post slug collision')


def fetch_head(head):
    git('fetch', '--no-tags', '--depth=1000', 'https://github.com/' + policy.REPO + '.git', head)


def prepare(pr, base, output, manifest, fetcher=fetch_head):
    policy.metadata(pr)
    policy.require(policy.SHA.fullmatch(base) and base == pr['base']['sha'], 'base changed')
    head = pr['head']['sha']
    policy.require(git('rev-parse', 'HEAD').decode().strip() == base, 'checkout not trusted base')
    # Public URL is fixed; never use a contributor-supplied clone URL or branch name.
    fetcher(head)
    policy.require(git('merge-base', base, head).decode().strip() == base,
                   'branch must include current main; rebase/update then revalidate')
    raw = git('diff', '--name-status', '-z', '--no-renames', base, head).split(b'\0')
    files = []
    for i in range(0, len(raw) - 1, 2):
        status, path = raw[i].decode('ascii'), raw[i + 1].decode('utf-8')
        policy.require(status in ('A', 'M'), 'unsupported operation')
        files.append({'filename': path, 'status': {'A': 'added', 'M': 'modified'}[status]})
    policy.file_policy(files)
    policy.require(len(files) == pr['changed_files'], 'changed-file mismatch')
    paths = git('ls-tree', '-r', '--name-only', '-z', head).decode().rstrip('\0').split('\0')
    check_slugs(paths, [f['filename'] for f in files])
    validated = []
    posts = []
    total = 0
    for item in files:
        path = item['filename']
        entry = git('ls-tree', '-z', head, '--', path).decode().rstrip('\0')
        mode, typ, rest = entry.split(' ', 2)
        oid, actual_path = rest.split('\t', 1)
        policy.require(actual_path == path, 'tree entry mismatch')
        if item['status'] == 'modified':
            prior = git('ls-tree', '-z', base, '--', path).decode()
            policy.require(prior.startswith('100644 blob '), 'mode change from unsafe base entry')
        size = int(git('cat-file', '-s', oid))
        check_entry(mode, typ, size, path)
        total += size
        policy.require(total <= policy.MAX_TOTAL, 'aggregate byte limit')
        data = git('cat-file', 'blob', oid)
        if policy.POST.fullmatch(path):
            links = policy.post(path, data)
            slug = Path(path).stem[11:]
            posts.append({'path': path, 'page': '/posts/' + slug + '/', 'links': links})
        elif policy.EXAMPLE.fullmatch(path):
            policy.example(path, data)
        else:
            policy.image(path, data)
        validated.append((path, data))
    policy.require(not output.exists(), 'snapshot path already exists')
    output.mkdir(parents=True)
    # Archive only trusted base. Nothing from PR tree is extracted or executed.
    archive = git('archive', '--format=tar', base)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(output, filter='data')
    for path, data in validated:
        target = output / path
        policy.require(target.resolve().is_relative_to(output.resolve()), 'overlay escape')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest.write_text(json.dumps({'base': base, 'head': head, 'files': files, 'posts': posts}, indent=2))
    print(json.dumps({'result': 'content-policy-passed', 'files': len(files), 'bytes': total,
                      'head': head, 'base': base}))


def check_markdown(body):
    """Exact production renderer plus bounded syntax-only fence checks, no eval."""
    import ast
    from markdown_it import MarkdownIt
    import yaml
    for token in MarkdownIt('commonmark').parse(body):
        if token.type != 'fence':
            continue
        language = token.info.lower()
        if language in ('python', 'py'):
            ast.parse(token.content)
        elif language in ('bash', 'sh'):
            result = subprocess.run(['bash', '--noprofile', '--norc', '-n'],
                                    input=token.content.encode(), capture_output=True, timeout=5,
                                    env={'PATH': '/usr/bin:/bin'})
            policy.require(result.returncode == 0, 'shell snippet syntax error')
        elif language == 'json':
            json.loads(token.content)
        elif language in ('yaml', 'yml'):
            yaml.safe_load(token.content)
        # Other languages are passive display, not a claim of language validation.
    result = subprocess.run(['bundle', 'exec', 'ruby', str(Path(__file__).with_name('render_check.rb'))],
                            input=json.dumps({'body': body}).encode(), capture_output=True, timeout=30)
    policy.require(result.returncode == 0, 'exact Kramdown safety check failed: ' + result.stderr.decode()[:500])
    return rendered_article('<div class="post-content">' + result.stdout.decode() + '</div>')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--event', type=Path, required=True)
    prep.add_argument('--base', required=True)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--manifest', type=Path, required=True)
    built = sub.add_parser('built')
    built.add_argument('--root', type=Path, required=True)
    built.add_argument('--manifest', type=Path, required=True)
    render = sub.add_parser('render')
    render.add_argument('--root', type=Path, required=True)
    render.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        event = json.loads(args.event.read_text())
        policy.require(event['repository']['full_name'] == policy.REPO, 'wrong event repo')
        prepare(event['pull_request'], args.base, args.output, args.manifest)
    elif args.command == 'render':
        report = json.loads(args.manifest.read_text())
        for item in report['posts']:
            text = (args.root / item['path']).read_text(encoding='utf-8')
            item['links'].extend(check_markdown(text[4:].split('\n---\n', 1)[1]))
        args.manifest.write_text(json.dumps(report, indent=2))
        print('Exact Kramdown AST/output and supported fence syntax checks passed.')
    else:
        report = json.loads(args.manifest.read_text())
        for post in report['posts']:
            page = args.root / post['page'].lstrip('/') / 'index.html'
            policy.require(page.is_file(), 'missing built post')
            actual_links = rendered_article(page.read_text(encoding='utf-8'))
            check_links(args.root, post['page'], [post['page'], *post['links'], *actual_links])
        print('Built changed-post pages, local asset/page links and fragments passed; external URLs syntax-only.')


if __name__ == '__main__':
    main()
