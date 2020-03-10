FROM python:3.8.1

# Create app directory
WORKDIR /project

# # Install app dependencies
# COPY webapp/requirements.txt ./

# RUN pip install -r requirements.txt

# Bundle app source
COPY . /project

RUN python setup.py install --skip-build
RUN pip install gunicorn==20.0.4

EXPOSE 5000
WORKDIR /project/webapp
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
