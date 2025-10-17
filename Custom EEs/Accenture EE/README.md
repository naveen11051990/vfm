# Building EE

```bash
sudo dnf install podman -y
sudo dnf install container-tools
podman login registry.redhat.io
podman login docker.io
podman build -f Dockerfile -t docker.io/jkdanielpraveen/accenture-custom-ee:1.0 .
podman push docker.io/jkdanielpraveen/accenture-custom-ee:1.0
```
