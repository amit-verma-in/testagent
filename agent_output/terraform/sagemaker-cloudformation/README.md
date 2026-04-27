# AWS SageMaker — CloudFormation (YAML)

Sample **AWS CloudFormation** templates for SageMaker (same style as `ecs-cloudformation/`).

| Template | What it deploys |
|----------|------------------|
| `sagemaker-notebook-minimal.yaml` | IAM role + **NotebookInstance** (VPC optional). |
| `sagemaker-inference-endpoint-minimal.yaml` | IAM role + **Model** + **EndpointConfig** + **Endpoint** (real-time inference). |

## Warnings

- **`AmazonSageMakerFullAccess`** on the notebook role is convenient for **labs only**; scope down for production (least privilege, VPC-only, no public internet where possible).
- Inference template expects a **valid** `InferenceImageUri` for your **region** and a **`ModelDataS3Uri`** pointing at model artifacts (e.g. `s3://bucket/prefix/model.tar.gz`).
- SageMaker pricing applies; tear down stacks when not in use.

## Deploy (CLI)

```bash
aws cloudformation deploy \
  --stack-name sagemaker-notebook-demo \
  --template-file sagemaker-notebook-minimal.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides EnvironmentName=demo-notebook VpcId=vpc-xxx SubnetId=subnet-xxx SecurityGroupId=sg-xxx

aws cloudformation deploy \
  --stack-name sagemaker-endpoint-demo \
  --template-file sagemaker-inference-endpoint-minimal.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvironmentName=demo-ep \
    InferenceImageUri=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.3.0-gpu-py311-cu121-ubuntu20.04-sagemaker \
    ModelDataS3Uri=s3://your-bucket/path/model.tar.gz
```

Image URIs are **region- and version-specific**; confirm in [SageMaker prebuilt Docker images](https://docs.aws.amazon.com/sagemaker/latest/dg/docker-registry-paths.html) for your account/region.

## After deploy

- **Notebook:** use stack output **NotebookInstanceName** and open the instance in the SageMaker console (or `CreatePresignedNotebookInstanceUrl`); CloudFormation does not expose a presigned Jupyter URL in outputs.
- **Endpoint:** invoke with `runtime.sagemaker` or the console **Test inference** (payload must match your model).
