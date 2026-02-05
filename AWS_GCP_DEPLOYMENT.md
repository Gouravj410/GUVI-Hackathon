# AWS & GCP Deployment Guide

This guide covers deploying the AI Voice Detector to AWS and Google Cloud Platform.

## Option 1: AWS Elastic Container Service (ECS)

### Prerequisites
- AWS account
- AWS CLI installed and configured
- Docker image pushed to ECR

### Step 1: Create ECR Repository

```bash
aws ecr create-repository --repository-name ai-voice-detector --region us-east-1
```

### Step 2: Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t ai-voice-detector .

# Tag image
docker tag ai-voice-detector:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-voice-detector:latest

# Push image
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-voice-detector:latest
```

### Step 3: Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name voice-detector-cluster --region us-east-1
```

### Step 4: Create IAM Role for ECS Task

```bash
# Create role
aws iam create-role --role-name ecsTaskRole --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam attach-role-policy --role-name ecsTaskRole --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

### Step 5: Create Task Definition

Create `task-definition.json`:
```json
{
  "family": "ai-voice-detector",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "voice-detector",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ai-voice-detector:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "API_KEY",
          "value": "YOUR_API_KEY_HERE"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/voice-detector",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register task definition:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### Step 6: Create Service

```bash
aws ecs create-service \
  --cluster voice-detector-cluster \
  --service-name voice-detector-service \
  --task-definition ai-voice-detector \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:targetgroup/voice-detector/xxxxx,containerName=voice-detector,containerPort=8000
```

### Step 7: Set Up Load Balancer

```bash
# Create ALB if not already done
aws elbv2 create-load-balancer \
  --name voice-detector-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx
```

---

## Option 2: Google Cloud Run

### Prerequisites
- Google Cloud account
- Cloud SDK installed
- Docker image ready

### Step 1: Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Build and Push to Artifact Registry

```bash
# Enable required APIs
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com

# Create repository
gcloud artifacts repositories create voice-detector \
  --repository-format=docker \
  --location=us-central1

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/voice-detector/app:latest .

# Push image
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/voice-detector/app:latest
```

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy voice-detector \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/voice-detector/app:latest \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 600 \
  --set-env-vars API_KEY=YOUR_API_KEY \
  --allow-unauthenticated
```

**Output**: You'll receive a service URL like `https://voice-detector-xxxxx-uc.a.run.app`

### Step 4: Configure Auto-scaling

```bash
gcloud run services update voice-detector \
  --max-instances 10 \
  --min-instances 1 \
  --region us-central1
```

### Step 5: Set Up Cloud Monitoring

```bash
gcloud monitoring dashboards create --config-from-file=- <<EOF
{
  "displayName": "Voice Detector Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\"",
                  "aggregation": {"alignmentPeriod": "60s"}
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
```

---

## Option 3: Google Cloud App Engine

### Prerequisites
- Google Cloud SDK
- `app.yaml` configuration file

### Step 1: Create `app.yaml`

```yaml
runtime: python310
entrypoint: gunicorn -w 4 -b :$PORT voice_detector.app:app

env: standard
instances: 1
automatic_scaling:
  min_instances: 1
  max_instances: 10

env_variables:
  API_KEY: "YOUR_API_KEY"
```

### Step 2: Deploy

```bash
gcloud app deploy
```

**Output**: Your service will be available at `https://YOUR_PROJECT_ID.appspot.com`

---

## Monitoring & Logging

### AWS CloudWatch

```bash
# View logs
aws logs tail /ecs/voice-detector --follow

# Create metric alarm
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --alarm-description "Alert when error rate is high" \
  --metric-name ErrorCount \
  --namespace AWS/ECS \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

### Google Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=voice-detector" --limit 50 --format json

# View real-time logs
gcloud logging read --follow --limit 50
```

---

## Performance Optimization

### AWS ECS
- Use Fargate Spot for cost savings (up to 70% discount)
- Enable auto-scaling based on CPU/memory
- Use CloudFront for API responses caching

### Google Cloud Run
- Cold starts: ~1-2 seconds (default)
- Warm starts: <100ms
- Use Cloud CDN for caching

---

## Cost Estimation

### AWS ECS (on-demand)
- Task: 512 CPU + 1GB RAM = ~$0.03/hour
- Load Balancer: ~$16/month
- **Estimated monthly**: $30-50 for 2 instances

### Google Cloud Run
- Per request: $0.00002400
- Per GB-second: $0.00001667
- **10,000 requests/day x avg 2s**: ~$0.48/month

---

## Troubleshooting

### AWS ECS
- Check task logs in CloudWatch
- Verify security group allows port 8000 inbound
- Ensure task role has permissions

### Google Cloud Run
- Check Cloud Run logs in Cloud Console
- Verify service has required permissions
- Check quotas and limits

---

For more details:
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
