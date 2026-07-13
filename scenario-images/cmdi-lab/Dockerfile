FROM php:8.1-apache

RUN a2enmod rewrite

COPY index.php /var/www/html/
COPY flag.txt /var/www/html/

RUN chmod 644 /var/www/html/flag.txt
