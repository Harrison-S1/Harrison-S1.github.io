---
layout: post
title: "Build a snipe-it server on Ubuntu"
date: 2022-0-12 09:00:00 -0500
categories: [homelab, howto's, linux]
tags: [homelab,linux,howto's]
---

## Install and set up LAMP Stack\

**Update Ubuntu**

Update your server with:

```bash
sudo apt update && sudo apt upgrade -d
```


**Install Apache**

```bash
sudo apt install apache2 -y 
```

Enable Apache2 to run on system start up.

```bash
sudo systemctl enable apache2
```

**Install MariaDB**

```bash
sudo apt install mariadb-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

Set up a root user password and secure MariaDB with:

```bash
sudo mysql\_secure\_installation`
```

**Note make sure you document the password correctly.**
Create a database and a snipe-it user. Change to the root user with the command:

```bash
sudo su
```

Access the MariaDB console with

```bash
mysql -r root -p 
```

Create the user,database and give the user permissions to it:

```bash
CREATE DATABASE snipeit_data;
CREATE USER 'snipeit_user'@'localhost' IDENTIFIED BY 'PASSWORD';
GRANT ALL PRIVILEGES ON snipeit.* TO 'snipeit_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Note to change the \`PASSWORD\`to the password you are giving to the user for the DB. Make sure you document this. If you want to double check your database has been created, use the following commands:**

```bash
mysql -u user -p
MariaDB \[(none)\]> show databases;

Output:

+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| snipeit            |
+--------------------+
4 rows in set (0.000 sec)
```

**Install PHP**

```bash
sudo apt install php libapache2-mod-php php-mysql -y
```

You can check the version of the PHP installed with the following command;

```bash
root@sphinx:~# php -v
PHP 7.4.3 (cli) (built: Oct  6 2020 15:47:56) ( NTS )
Copyright (c) The PHP Group
Zend Engine v3.4.0, Copyright (c) Zend Technologies
   with Zend OPcache v7.4.3, Copyright (c), by Zend Technologies
```

## Install Snipe-IT

Install Extra PHP Extensions and other package required.

```bash
sudo apt install php-{bcmath,cli,xml,mbstring,tokenizer,curl,zip,ldap,gd} openssl curl git wget zip
```

Clone Snipe-IT from github and add it to the web dir.

```bash
git clone https://github.com/snipe/snipe-it.git /var/www/html/snipeit
```

**Snipe-IT set up**
Rename the Snipe-IT variables file .env.example to .env file.

```bash
cp /var/www/html/snipeit/.env.example /var/www/html/snipeit/.env
```

Open the environment configuration file.

```bash
vim /var/www/html/snipeit/.env
```

**Snipe-IT Application Settings**
Set the URL you will use to access your Snipe-IT, the Application language, Timezone. The URL should not have a trailing slash.
```bash
\# --------------------------------------------
\# REQUIRED: BASIC APP SETTINGS
\# --------------------------------------------
APP_ENV=production
APP_DEBUG=false
APP_KEY=ChangeMe
APP_URL=[http://servername.domain.com]
(http://servername.domain.com/)
APP_TIMEZONE='Europe/London'
APP_LOCALE=en
```

**Snipe-IT Database Settings**
Set the database host, database name, user and password created above,

```bash
\# --------------------------------------------
\# REQUIRED: DATABASE SETTINGS
\# --------------------------------------------
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_DATABASE=snipeit
DB\_USERNAME=snipeit\_user
DB_PASSWORD=P@SSWORD
DB_PREFIX=null
DB\_DUMP\_PATH='/usr/bin'
DB_CHARSET=utf8mb4
DB\_COLLATION=utf8mb4\_unicode_ci
```

If you are gonna need to send emails, configure Email Server setting as well.

**Install Required PHP Libraries**

```bash
cd /var/www/html/snipeit
curl -sS https://getcomposer.org/installer | php
php composer.phar install --no-dev --prefer-source
```

**Set dir ownership and given permission**

```bash
chown -R www-data:www-data /var/www/html/snipeit
```

**Generate Snipe-IT App Key**
The app key is a randomly generated key that app uses to encrypt data. The value generated will be assigned automatically to APP_KEY variable in the Snipe-IT configuration file.

```bash
php artisan key:generate

\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*
\*     Application In Production!     *
\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*

Do you really wish to run this command? (yes/no) \[no\]:
\> yes

Application key set successfully.

The key generated is automatically set as the value of the APP_KEY variable in the .env file.
```

**Configure Apache with SSL**

Note you will need to enable ssl for apache with:

```bash
sudo a2enmod ssl

vim /etc/apache2/sites-available/snipeit.conf
```
```bash
&lt;VirtualHost *:443&gt;
        DocumentRoot /var/www/html/snipeit/public
        ServerName SERVERNAME.domain.com

        SSLEngine on

        SSLCertificateFile /etc/apache2/ssl/NAMEOFCERT.cer
        SSLCertificateKeyFile /etc/apache2/ssl/NAMEOFCERT.key
        SSLCertificateChainFile /etc/apache2/ssl/NAMEOFCERT.cer 

        &lt;Directory /var/www/html/snipeit/public&gt;
                Allow From All
                AllowOverride None
                Options None
        &lt;/Directory&gt;

        RewriteEngine On
        RewriteCond %{DOCUMENT\_ROOT}%{REQUEST\_FILENAME} !-d
        RewriteCond %{REQUEST_URI} (.+)/$
        RewriteRule ^ %1 \[L,R=301\]
        RewriteCond %{DOCUMENT\_ROOT}%{REQUEST\_FILENAME} !-d
        RewriteCond %{DOCUMENT\_ROOT}%{REQUEST\_FILENAME} !-f
        RewriteRule ^ /index.php \[L\]

        ErrorLog ${APACHE\_LOG\_DIR}/snipeit-error.log
        CustomLog ${APACHE\_LOG\_DIR}/snipeit-access.log combined
&lt;/VirtualHost&gt;
```

**If you are not using SSL, then the config will be like this:**
```bash
&lt;VirtualHost *:80&gt; 
	DocumentRoot /var/www/html/snipeit/public
	ServerName SERVERNAME.domain.com

	&lt;Directory /var/www/html/snipeit/public&gt;
		Allow From All
		AllowOverride None
		Options None
	&lt;/Directory&gt;

	RewriteEngine On
	RewriteCond %{DOCUMENT\_ROOT}%{REQUEST\_FILENAME} !-d
	RewriteCond %{REQUEST_URI} (.+)/$
	RewriteRule ^ %1 \[L,R=301\]
	RewriteCond %{DOCUMENT\_ROOT}%{REQUEST\_FILENAME} !-d
	RewriteCond %{DOCUMENT\_ROOT}%{REQUEST\_FILENAME} !-f
	RewriteRule ^ /index.php \[L\]

	ErrorLog ${APACHE\_LOG\_DIR}/snipeit-error.log
	CustomLog ${APACHE\_LOG\_DIR}/snipeit-access.log combined
&lt;/VirtualHost&gt;
```

Save the configuration file and run a file syntax test.

```bash
apachectl configtest
```
If the command return, Syntax Ok, proceed. Otherwise fix the would errors.

Enable Snipe-IT site configuration.

```bash
a2ensite snipeit.conf

```

Enable Rewrite module.

```bash
a2enmod rewrite
```

Restart Apache

```bash
systemctl restart apache2
```

Allow through the firewall

```bash
sudo ufw allow 443
sudo ufw reload
```

**Snipe-IT Pre-Flight & Setup** Run the pre-flight setup to verify that all configurations are correct. You can access Snipe-IT pre-flight page from the URL; http://&lt;Hostname or Address&gt;.