# memoryapp

## Where can I deploy these agents?

You can deploy the agents anywhere you can run a Python service, including:

- **Local VM or bare-metal server** (Linux/macOS/Windows)
- **Docker-based platforms** (AWS ECS/Fargate, Google Cloud Run, Azure Container Apps, Render, Railway, Fly.io)
- **Kubernetes clusters** (EKS, GKE, AKS, self-managed)
- **Serverless functions** for lightweight/background tasks (AWS Lambda, Google Cloud Functions, Azure Functions)

If you're just starting, a Docker container on Cloud Run, Render, or Railway is usually the quickest path.

## Deploy to Azure Container Apps

You can deploy these agents to Azure Container Apps with a container image:

```bash
# Requires a Dockerfile in the repository root.
az login
az group create --name memoryapp-rg --location eastus
# ACR names are globally unique in Azure.
ACR_NAME="memoryappacr$(date +%s)"
az acr create --resource-group memoryapp-rg --name "$ACR_NAME" --sku Basic
az acr build --registry "$ACR_NAME" --image memoryapp:latest .
az containerapp env create --name memoryapp-env --resource-group memoryapp-rg --location eastus
az identity create --name memoryapp-mi --resource-group memoryapp-rg
IDENTITY_ID=$(az identity show --name memoryapp-mi --resource-group memoryapp-rg --query id -o tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show --name memoryapp-mi --resource-group memoryapp-rg --query principalId -o tsv)
ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group memoryapp-rg --query id -o tsv)
az role assignment create --assignee-object-id "$IDENTITY_PRINCIPAL_ID" --assignee-principal-type ServicePrincipal --scope "$ACR_ID" --role AcrPull
az containerapp create \
  --name memoryapp \
  --resource-group memoryapp-rg \
  --environment memoryapp-env \
  --image "$ACR_NAME.azurecr.io/memoryapp:latest" \
  --target-port 8000 \
  --ingress external \
  --registry-server "$ACR_NAME.azurecr.io" \
  --user-assigned "$IDENTITY_ID" \
  --registry-identity "$IDENTITY_ID"
```

Get the app URL:

```bash
az containerapp show --name memoryapp --resource-group memoryapp-rg --query properties.configuration.ingress.fqdn -o tsv
```

## Interact with deployed agents

Expose one orchestrator endpoint (for example `POST /run`) that coordinates all specialist agents internally. At minimum, that endpoint should:

- accept the user goal
- invoke planner/builder/deployer agents in sequence (or graph)
- return progress and final output

Then call:

```bash
curl -X POST "https://<your-container-app-fqdn>/run" \
  -H "Content-Type: application/json" \
  -d '{"goal":"Create and deploy a software solution","mode":"multi-agent"}'
```

This lets you interact with one public API while the agents talk to each other behind the endpoint to plan, build, and deploy.
