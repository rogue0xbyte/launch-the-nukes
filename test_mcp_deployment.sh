#!/bin/bash
# Quick script to test MCP access in deployed worker

set -e

PROJECT_ID="launch-the-nukes"
REGION="us-central1"

echo "🔧 Building and deploying worker with MCP test..."

# Build new worker image with test files
gcloud builds submit --tag gcr.io/$PROJECT_ID/launch-the-nukes-worker-test:latest .

# Create a temporary job configuration for testing
cat > test-job.yaml <<EOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: mcp-test-job
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    spec:
      template:
        spec:
          containers:
          - image: gcr.io/$PROJECT_ID/launch-the-nukes-worker-test:latest
            command: ["/bin/bash"]
            args: ["-c", "/app/test_mcp_in_worker.sh"]
            env:
            - name: GOOGLE_CLOUD_PROJECT
              value: "$PROJECT_ID"
            resources:
              limits:
                cpu: "1"
                memory: "1Gi"
EOF

echo "🧪 Running MCP test job..."
gcloud run jobs replace test-job.yaml --region=$REGION

# Execute the job
gcloud run jobs execute mcp-test-job --region=$REGION --wait

echo "📋 Getting job logs..."
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=mcp-test-job" --limit=50 --format="value(textPayload)" --freshness=5m

# Cleanup
rm -f test-job.yaml
echo "🧹 Cleaning up test job..."
gcloud run jobs delete mcp-test-job --region=$REGION --quiet
