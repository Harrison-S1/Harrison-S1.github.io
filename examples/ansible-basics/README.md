# Runnable Ansible basics examples

Prerequisites: Linux controller with Python supported by the pinned ansible-core; tested controller used Python 3.14.4 and ansible-core 2.22.0. Python 3.14 is required to reproduce the exact interpreter used, not asserted as the universal minimum. See the official support matrix for other supported combinations. `/usr/bin/python3` must exist (or adjust inventory.ini).

From this directory, on a normal local filesystem:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
ansible --version
ansible-playbook -i inventory.ini 01-facts.yml
ansible-playbook -i inventory.ini 02-files.yml
ansible-playbook -i inventory.ini 02-files.yml
ansible-playbook -i inventory.ini 03-template.yml
ansible-playbook -i inventory.ini 03-template.yml
```

Examples 1–3 use the current user without sudo or SSH. Local connection is your real controller, NOT an isolated VM. Examples 2–3 create/overwrite only `sandbox/hello.txt` and `sandbox/greeting.txt` by default. Do not point `demo_dir` at important files. The modes are public demo modes, not suitable for secrets. A later run restores managed contents if manually edited.

## Privileged optional example: nginx

04-nginx.yml is a separate, combined package/template/service/handler example. Inventory group `web` is intentionally empty. Add ONLY a disposable Debian/Ubuntu VM using SSH, with a Python interpreter, python3-apt already installed, working sudo rights, apt repositories and a functioning service manager. It overwrites /var/www/html/index.html, installs nginx (which can start it), and enables/starts the service. Review existing port-80 use first. Never add localhost to web. No keys, passwords or real addresses are committed.

```sh
ansible-playbook -i inventory.ini 04-nginx.yml --syntax-check
# After adding your disposable VM to [web], preview only:
ansible-playbook -i inventory.ini 04-nginx.yml --check --diff -K
# Deliberately apply ONLY to that VM after reviewing the preview:
ansible-playbook -i inventory.ini 04-nginx.yml -K
```

`-K` prompts for a become password; it does not grant sudo permission. `become: true` requests escalation. The apt dependency auto-install option is disabled explicitly. The handler reloads nginx only when the HTML template reports a change, normally at the end of the play. This demonstrates notification mechanics; nginx serves changed static HTML without needing a reload, so this reload is educational rather than an operational requirement. HTML variables are escaped with Jinja's `e` filter.

## Recorded verification and limits

All four playbooks passed syntax checking. Facts ran on Ubuntu 26.04. File example first/second runs: changed=2/0; template: changed=1/0, with exact output bytes verified. A dedicated task-local fixture replaced the default sandbox for these runs. Modes on the CIFS fixture filesystem are not enforced normally: the subsequent --check --diff predicted mode changes despite the unchanged real second runs. Do not claim permission enforcement or a universally clean check preview from this test.

The nginx --check invocation used the empty web group and skipped all tasks: no apt, template, service or handler execution was validated. No real privileged target, Debian host or alternate distribution was tested. Syntax success is not runtime verification. Check mode is a simulation, not isolation; it can be incomplete, particularly when later tasks depend on files/packages only predicted by earlier tasks. --diff can expose file contents. No full Jekyll build was available.

The dependency lock records the actual installed versions; package state=present does not pin nginx's distro package version. See the companion article for official sources.
