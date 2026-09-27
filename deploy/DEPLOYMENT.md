# Deployment

The app is live at **https://d98o1wtikf6a7.cloudfront.net/**.

## Architecture

One CloudFront distribution is the single public HTTPS entry point. It
splits traffic by path:

- **Everything except `/api/*`** → a private S3 bucket holding the built
  React app, accessed via an Origin Access Control (OAC) - the bucket has
  no public access at all; only this specific distribution can read from
  it. A CloudFront Function rewrites any extensionless path (like
  `/dashboard`) to `/index.html`, so client-side routes survive a page
  refresh.
- **`/api/*`** → an EC2 instance running the backend in a Docker
  container, over plain HTTP on port 80 (CloudFront still serves the
  *public* side over HTTPS - this hop is inside AWS's network). Caching is
  disabled for this behavior (`Managed-CachingDisabled`) since API
  responses shouldn't be cached, and the origin request policy
  (`Managed-AllViewerExceptHostHeader`) forwards the `Authorization` header
  through to the backend.

```
Browser
  │  HTTPS
  ▼
CloudFront (d98o1wtikf6a7.cloudfront.net)
  │                              │
  │ default behavior             │ /api/* behavior
  ▼                              ▼
S3 bucket                    EC2 instance (t4g.micro)
(React build, via OAC)       Docker container, port 80 → 8000
                                   │
                                   │ port 5432 (backend SG → db SG only)
                                   ▼
                             RDS PostgreSQL (private, no public access)
```

The backend reads its configuration from environment variables sourced
from **SSM Parameter Store** (`/paper-trading/prod/*`, all `SecureString`)
at deploy time - nothing sensitive lives in the EC2 user data, the Docker
image, or git.

## Resources

| Resource | Name / ID | What it does |
|---|---|---|
| CloudFront distribution | `EMKKYWCQZYX6A` | The public HTTPS URL; routes `/api/*` to EC2, everything else to S3 |
| CloudFront Function | `paper-trading-spa-rewrite` | Rewrites extensionless paths to `/index.html` so React Router routes survive a refresh |
| Origin Access Control | `paper-trading-oac` | Lets CloudFront read the private S3 bucket; nothing else can |
| S3 bucket | `paper-trading-frontend-360496494099` | Holds the built frontend (`index.html`, hashed JS/CSS, favicon) |
| EC2 instance | `i-0325da4aea57d014d` (t4g.micro, Amazon Linux 2023 ARM) | Runs the backend Docker container |
| Elastic IP | `52.202.184.145` | Fixed address for the EC2 instance, so CloudFront's origin config never breaks on instance restart |
| RDS PostgreSQL | `paper-trading-db` (db.t4g.micro, Single-AZ, 20 GiB gp3, encrypted) | The production database |
| Security group | `paper-trading-ec2-sg` | Inbound port 80, only from CloudFront's IP range |
| Security group | `paper-trading-db-sg` | Inbound port 5432, only from `paper-trading-ec2-sg` |
| IAM role + instance profile | `paper-trading-ec2-role` / `paper-trading-ec2-profile` | Lets EC2 use SSM (no SSH) and read only its own secrets |
| SSM parameters | `/paper-trading/prod/{DATABASE_URL,JWT_SECRET,FINNHUB_API_KEY,DEMO_PASSWORD}` | All secrets, `SecureString` type |

All resources are tagged `Project=paper-trading`.

## Server access

There is no SSH access and port 22 is not open anywhere. All server
administration goes through **AWS Systems Manager** (SSM Run Command),
which uses the EC2 instance's IAM role rather than a key pair - so access
is controlled entirely through IAM, and every command run on the box is
logged.

## Cost estimate

Assuming the EC2 and RDS instances run 24/7:

| Resource | Est. monthly cost |
|---|---|
| EC2 t4g.micro | ~$6 |
| RDS db.t4g.micro (Single-AZ) | ~$12 |
| RDS storage (20 GiB gp3) | ~$2 |
| S3 + CloudFront (low traffic, PriceClass_100) | ~$1-3 |
| Everything else (SSM, Elastic IP while attached, etc.) | ~$0 |
| **Total** | **~$22-26/month** |

Check the AWS Billing dashboard after a few days to confirm actual costs
match this estimate.

## Redeploying

**Backend** (after pushing new backend code to `paper-trading-app`):

```bash
./deploy/redeploy-backend.sh
```

Pulls the latest code onto the EC2 instance via SSM, rebuilds the Docker
image, and restarts the container. Verifies `/api/health` at the end.

**Frontend** (after any frontend change):

```bash
./deploy/redeploy-frontend.sh
```

Builds with `VITE_API_URL=/api`, syncs to S3 with the right cache headers,
and invalidates CloudFront so the change is live immediately.

Both scripts read resource IDs from `deploy/.deploy-state` (gitignored,
regenerate from the AWS console/CLI if you ever lose it - no secrets are
in it).

## Retrieving the demo password

```bash
aws ssm get-parameter --name "/paper-trading/prod/DEMO_PASSWORD" --with-decryption --region us-east-1 --query "Parameter.Value" --output text
```

The demo account's email is `demo@papertrading.app`.

## Tearing everything down

```bash
./deploy/teardown.sh
```

Deletes every resource above, in dependency order (CloudFront first, since
disabling it is the slowest step; IAM and SSM last). Asks you to type
`paper-trading` to confirm, and offers to take a final RDS snapshot before
deleting the database. This is destructive and mostly irreversible - only
run it when you're done with the project for good (or ready to redeploy
from scratch).
