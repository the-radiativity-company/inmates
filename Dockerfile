FROM python:3.8.1

# Create project directory
WORKDIR /project

# Bundle project source
COPY . /project

# Provisioning
RUN python setup.py install --skip-build
RUN pip install gunicorn==20.0.4

# Ignored by heroku
EXPOSE 5000

WORKDIR /project/webapp
CMD gunicorn --bind 0.0.0.0:$PORT wsgi:app
