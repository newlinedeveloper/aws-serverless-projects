# 📸🎥 Serverless Media Processing with AWS CDK

This project implements a **serverless application** for **image & video processing** using **AWS Rekognition, S3, DynamoDB, SNS, and Lambda**.
It automatically detects labels for images and videos uploaded to S3, stores the results in DynamoDB, and sends notifications via SNS.

---

## 🚀 Features

* **Image Processing** → Detects objects/labels in uploaded images using Rekognition.
* **Video Processing** → Starts Rekognition Video label detection for uploaded videos.
* **Results Storage** → Saves metadata & labels into DynamoDB.
* **Notifications** → Sends results to an SNS topic (e.g., email).
* **Serverless** → Scales automatically, pay-per-use.

---

## 📂 Project Structure

```
media-processing-cdk/
├── app.py                 # CDK app entry
├── requirements.txt       # Python dependencies
└── serverless_app_stack.py  # CDK stack with all AWS resources
```

---

## 🛠️ How to Create This Project

1. **Install prerequisites**

   * [Python 3.11+](https://www.python.org/downloads/)
   * [AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)
   * AWS CLI (`aws configure`) with credentials set

   ```bash
   npm install -g aws-cdk
   ```

2. **Create project folder & initialize CDK**

   ```bash
   mkdir media-processing-cdk && cd media-processing-cdk
   cdk init app --language python
   ```

3. **Install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Update `requirements.txt` to include:

   ```txt
   aws-cdk-lib
   constructs
   ```

4. **Add the stack code**
   Replace `serverless_app_stack.py` with the code you provided (contains S3, Lambda, Rekognition, DynamoDB, SNS).

5. **Bootstrap & Deploy**

   ```bash
   cdk bootstrap
   cdk deploy
   ```

   CDK will output the S3 bucket name created.

---

## 📌 Details About This Project

* **S3 Bucket** → Upload media files (`.jpg`, `.jpeg`, `.png`, `.mp4`, `.mov`, `.avi`).
* **Lambda (`MediaProcessorLambda`)** →

  * For **images**: Calls `rekognition.detect_labels` → saves labels in DynamoDB → sends SNS notification.
  * For **videos**: Calls `rekognition.start_label_detection` → polls `get_label_detection` until job finishes → saves results in DynamoDB → sends SNS notification.
* **DynamoDB** → Stores file name, type (image/video), detected labels, and status.
* **SNS** → Sends processing results to your email (subscribed in stack).

---

## 🧪 How to Test

1. **Upload a test image**

   ```bash
   aws s3 cp test.jpg s3://<MediaBucketName>
   ```

   * Lambda is triggered.
   * Rekognition detects labels.
   * DynamoDB stores results.
   * SNS sends email with detected labels.

2. **Upload a test video**

   ```bash
   aws s3 cp sample.mp4 s3://<MediaBucketName>
   ```

   * Lambda starts Rekognition Video label detection.
   * Job runs asynchronously, results are fetched & stored in DynamoDB.
   * SNS sends notification when done.

3. **Check DynamoDB**

   ```bash
   aws dynamodb scan --table-name MediaResultsTable
   ```

   You’ll see entries like:

   ```json
   {
     "fileName": "test.jpg",
     "type": "image",
     "labels": ["Person", "Car", "Tree"],
     "status": "IMAGE_PROCESSED"
   }
   ```

   Or for video:

   ```json
   {
     "fileName": "sample.mp4",
     "type": "video",
     "labels": ["Dog", "Running", "Park"],
     "status": "VIDEO_PROCESSED"
   }
   ```

---
