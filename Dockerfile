# Start with a base image
FROM python:3.8-slim

# Set a directory for the app
WORKDIR /usr/src/app

# Copy all files to the app directory
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available
EXPOSE 5000

# Run the app
CMD ["python", "./app.py"]
