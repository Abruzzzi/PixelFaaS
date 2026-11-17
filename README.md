# PixelFaaS

CSE 4207 final project: serverless image resizing and compression using OpenFaaS, Python, and Pillow.

## Status
- Minikube and OpenFaaS are running locally.
- Python starter function deployed successfully.
- Current response: `Hello from OpenFaaS!`
- Image processing and frontend integration are next.

## Files
- `image-process/handler.py`: function code
- `image-process/requirements.txt`: dependencies
- `stack.yaml`: build and deployment settings
- `template/python3-http/`: function template

## Run
Requires Docker, Minikube, and OpenFaaS already installed.

```bash
minikube start
kubectl port-forward -n openfaas svc/gateway 8080:8080
```

Keep port forwarding running. In another terminal:

```bash
curl http://localhost:8080/function/image-process
```

## Update and deploy
Update the image tag in `stack.yaml`, then build, push, and deploy using that same tag:

```bash
faas-cli build -f stack.yaml
docker push og4real/image-process:v2
faas-cli deploy -f stack.yaml --gateway http://localhost:8080
```

Requires Docker Hub and OpenFaaS login.

## Team workflow
Backend teammates push Python code changes to GitHub. The infrastructure lead builds, publishes, and deploys the updated image.
