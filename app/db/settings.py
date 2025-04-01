from dotenv import load_dotenv
import os
from sshtunnel import SSHTunnelForwarder
load_dotenv()

ssh_tunnel= SSHTunnelForwarder(
    os.getenv('SERVER_IP'),
    ssh_username=os.getenv('SSH_USERNAME'),
    ssh_password=os.getenv('SSH_PASSWORD'),
    remote_bind_address=('localhost',3306)
)
ssh_tunnel.start()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE'),
        'USER': os.getenv('MYSQL_USER'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    },
    'sshtunnel_db':{
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE'),
        'USER': os.getenv('MYSQL_USER'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD'),
        'HOST': 'localhost',
        'PORT': ssh_tunnel.local_bind_port,
    },
}