FROM python:3.13-slim-bookworm
WORKDIR /usr/pic2map
# Install exiftool and libmagic1 for image metadata extraction.
RUN apt-get update && apt-get install -y exiftool libmagic1
# Install Python dependencies.
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
# Where the database is stored.
ADD database database
# Application code.
ADD pic2map pic2map
# Launch pic2map server.
CMD ["python", "-m", "pic2map.cli", "server"]