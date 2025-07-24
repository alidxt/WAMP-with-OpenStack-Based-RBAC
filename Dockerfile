# Use a Python 3.10 base image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include the /app directory, allowing Python to find modules
ENV PYTHONPATH /app

# Removed: RUN mkdir -p .crossbar
# Removed: RUN echo '{ ... }' > .crossbar/config.json

# Copy the rest of the application code (including .crossbar/config.json from host)
COPY . .

# Expose the port Flask app runs on (Mock Keystone)
EXPOSE 5000

# No default command here, as each service in docker-compose will define its own command.
