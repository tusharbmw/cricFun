# CricFun
Using Django to make a app to be used/tested with friends

#setup steps:
update db info in cricBet settings.py

to update changes use

python manage.py makemigrations

python manage.py migrate -- to create db

To run on server:
python manage.py runserver 0.0.0.0:5000 &



open firewall: 

sudo iptables --list --line-numbers

iptables -P INPUT ACCEPT

iptables -P OUTPUT ACCEPT

iptables -P FORWARD ACCEPT

iptables -F

To renew certificate
sudo certbot renew --nginx

Start gunicorn (from /home/opc/cricBet)

nohup bin/gunicorn_start &

For linux you will may have to so that nginx can access reverse proxy
sudo setsebool -P httpd_can_network_connect 1

And
sudo semanage permissive -a httpd_t


Oracle: 
Need to grant access to tablespace to user
GRANT UNLIMITED TABLESPACE TO user;
