# INF2003-Project
Database Systems Project

Install Django & psycopg2 (PostgreSQL adapter for python): 
pip install django psycopg2-binary

Generate Migrations files everytime you make changes to the models.py: 
python manage.py makemigrations

Apply the migrations to create tables in PostgreSQL database: 
python manage.py migrate

Run the Django server to test app:
python manage.py runserver

Access the app via localhost:8000. & localhost:8000/admin to go to the admin login page.
I created an admin of name: admin pw: ciscoclass.