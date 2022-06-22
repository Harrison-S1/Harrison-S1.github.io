---
layout: post
title: "Backup & restore MYSQL MariaDB databases"
date: 2022-02-09 09:00:00 -0500
categories: [homelab,howto's,linux]
tags: [homelab,ubuntu,howto's,backups]
---

#### Backing up

```bash
mysqldump --add-drop-table --databases mydatabase_db > /home/wiki/db/$(/bin/date +\\%Y-\\%m-\\%d).sql.bak
```

- mysqldump is the backup tool [Read More](https://mariadb.com/kb/en/library/mysqldump/)
- add-drop-table removes one or more tables [Read More](https://mariadb.com/kb/en/library/drop-table/)
- --databases is defining the db name, i.e.mydatabase_db
- \> Forward this output to the /path/the/folder

#### Restoring

```bash
mysql -u root mydatabase_db  < 2019-09-10.sql.bak
```

Your location my be more like /path/to/file/2019-09-10.sql.bak