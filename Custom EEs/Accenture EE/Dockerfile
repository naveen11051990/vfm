# Dockerfile

# 1. Start from the default AAP-supported EE base
FROM registry.redhat.io/ansible-automation-platform-26/ee-supported-rhel9:latest

# 2. Install system packages (using microdnf)
USER root
RUN microdnf install -y python3-pip python3-setuptools && microdnf clean all

# 3. Install Galaxy collections via ansible-galaxy
#    Adjust this path if your collections directory differs
COPY requirements.yml /tmp/requirements.yml
RUN ansible-galaxy collection install -r /tmp/requirements.yml

# 4. Install Python packages via pip
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt

# 5. (Optional) Clean up caches
RUN rm -rf /var/cache/dnf \
    /root/.cache/pip \
    /tmp/requirements.yml \
    /tmp/requirements.txt

# 6. Switch back to the default non-root user if desired
USER 1001